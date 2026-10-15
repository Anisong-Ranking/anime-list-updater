# anison-rankin: アニメ一覧の YouTube URL 探索を「このPCの住宅IP」で実行し push する定時タスク本体。
# 背景: クラウド(GitHub Actions)はデータセンターIPが YouTube に「ボット」判定され検索が全滅する。
#        住宅IP(このPC)では検索が通るので、URL 探索だけここで回して結果をリポジトリへ push する。
# 認証: git push はユーザーの資格情報(gh / 資格情報マネージャー)を使う。タスクは「ログオン時のみ実行」で登録する。
# 注意: git は通常メッセージ(From .../ Updating ...)を stderr に出す。これを PowerShell の
#        ErrorActionPreference=Stop が誤って「エラー」と判定し止まるため、ネイティブ実行は
#        ErrorActionPreference=Continue にして $LASTEXITCODE で明示判定する。

$repo   = 'E:\wk\02.AnisongRanking\pipeline\anime_list_updater'
$logDir = 'E:\wk\02.AnisongRanking\persistent\logs'
$ts     = Get-Date -Format 'yyyy-MM-dd_HHmmss'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "url_finder_$ts.log"

function Log($m) {
    $line = '{0}  {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    # 注意: Write-Output は関数の戻り値(成功ストリーム)を汚し、Invoke-Native の
    # 戻り値にログ文字列が混ざって終了コード判定を壊す。コンソールには Write-Host で出す。
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

# ネイティブコマンドを実行し、出力をログに流し、終了コードを返す(stderr で止まらない)。
function Invoke-Native {
    param([Parameter(Mandatory)][string]$Exe, [string[]]$CmdArgs)
    $ErrorActionPreference = 'Continue'
    & $Exe @CmdArgs 2>&1 | ForEach-Object { Log $_ }
    return $LASTEXITCODE
}

Log 'START url finder (PC residential IP)'
$failed = $false
try {
    if (-not (Test-Path $repo)) { throw "repo not found: $repo" }
    Set-Location -LiteralPath $repo

    # 実行環境を明示的に固定(検証済み): システム Python 3.10 は updater の依存
    # (requests/bs4/lxml/pandas/openpyxl/dateutil)と yt-dlp.exe を両方持つ。
    # その Scripts を PATH 先頭へ置き、updater が呼ぶ素の `yt-dlp` をこの版に固定する。
    $pyHome    = 'C:\Users\bboyi\AppData\Local\Programs\Python\Python310'
    $pyScripts = Join-Path $pyHome 'Scripts'
    $py = Join-Path $pyHome 'python.exe'
    if (-not (Test-Path $py)) { throw "python not found: $py" }
    $env:Path = "$pyScripts;$pyHome;$env:Path"
    # Windows 既定の cp932 では YouTube タイトルの絵文字(⚡等)を print できず
    # UnicodeEncodeError でクラッシュする。クラウド同様 UTF-8 を強制する。
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'

    $ytv = (& yt-dlp --version 2>&1 | Out-String).Trim()
    Log "yt-dlp version: $ytv"

    # 最新コード/データ取得(origin と同期してから push しないと非fast-forwardで弾かれる)
    Log 'git pull...'
    if ((Invoke-Native 'git' @('pull','--ff-only')) -ne 0) { throw 'git pull failed' }

    # アニメ一覧スクレイプ + YouTube URL 探索 + CSV 出力
    Log 'run updater (scrape + youtube search)...'
    if ((Invoke-Native $py @('-m','src.main','--seasons','current,next')) -ne 0) { throw 'updater failed' }

    # クラウド②(pipeline.yml)がこのリポジトリを clone した時、①が「今日ちゃんと成功したか」を
    # 見分けられるよう、成功時刻(UTC)を記録する(#345)。ここまで来ていれば scrape+検索は成功して
    # いるので書く。失敗時(throw で catch に落ちた場合)はここを通らず、古いタイムスタンプの
    # ままリポジトリに残るので、②側はそれを見て鮮度チェックできる。
    # BOMなしUTF-8で書く(Set-Content -Encoding utf8 はBOM付きになり、②側のPython
    # json.load がBOM混入で読めなくなる。#328の日次レポート保険と同じ罠)。
    $statusPath = Join-Path $repo 'data\_pc_url_finder_status.json'
    $utcNow = (Get-Date).ToUniversalTime().ToString('o')
    $statusJson = '{"last_success_utc": "' + $utcNow + '"}'
    [System.IO.File]::WriteAllText($statusPath, $statusJson, (New-Object System.Text.UTF8Encoding($false)))

    # 変更があれば commit & push(GitHub Actions の push 段と同等)
    Invoke-Native 'git' @('add','data/') | Out-Null
    $ErrorActionPreference = 'Continue'
    & git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $date = Get-Date -Format 'yyyy-MM-dd'
        if ((Invoke-Native 'git' @('commit','-m',"auto: anime list update (PC) $date")) -ne 0) { throw 'git commit failed' }
        # push 認証: 定時タスク(非対話)では資格情報マネージャーが /dev/tty をプロンプトして失敗する
        #   (2026-07-12 真因: fatal: could not read Password for 'https://x-access-token@github.com')。
        #   成功実績のある run_season_dating.ps1 と同じく gh のトークンを明示URLに埋めて push する。
        #   `-c credential.helper=` で資格情報マネージャーを無効化(プロンプト回避)。git は自身の
        #   出力からURL内の資格情報を伏字化するのでログに漏れない。トークンは .git/config に書かない。
        #   gh は -NoProfile 起動だとPATHに無いことがあるため絶対パスで解決する。
        $ghExe = if (Get-Command gh -ErrorAction SilentlyContinue) { (Get-Command gh).Source }
                 elseif (Test-Path 'C:\Users\bboyi\bin\gh.exe') { 'C:\Users\bboyi\bin\gh.exe' }
                 else { $null }
        if (-not $ghExe) { throw 'gh.exe not found (needed for push auth)' }
        $ghtoken = (& $ghExe auth token).Trim()
        if (-not $ghtoken) { throw 'gh auth token empty' }
        $origin  = (& git remote get-url origin).Trim()
        $slug    = ($origin -replace '^.*github\.com[/:]','') -replace '\.git$',''
        $authurl = "https://x-access-token:$ghtoken@github.com/$slug.git"
        git -c credential.helper= push $authurl HEAD *>> $log
        if ($LASTEXITCODE -ne 0) { throw 'git push failed' }
        Log 'pushed changes'
    } else {
        Log 'no changes to commit'
    }
    Log 'END ok'
} catch {
    Log "ERROR: $_"
    $failed = $true
}

if ($failed) { exit 1 } else { exit 0 }
