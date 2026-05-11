# سكريبت إعداد Task Scheduler للتحديث التلقائي (Windows)
# ==========================================================
# 
# يقوم بإنشاء مهمة مجدولة في Windows لتشغيل flight_manager.py
# 
# الاستخدام:
#   1. افتح PowerShell كمسؤول (Run as Administrator)
#   2. cd إلى مجلد المشروع
#   3. .\setup_windows_task.ps1

# التأكد من تشغيل البرنامج كمسؤول
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ خطأ: يجب تشغيل هذا السكريبت كمسؤول (Run as Administrator)" -ForegroundColor Red
    Write-Host ""
    Write-Host "اضغط أي زر للخروج..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "║      إعداد التحديث التلقائي (Task Scheduler) - Windows  ║" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# الحصول على المسار الكامل
$ProjectDir = Get-Location
$ScriptPath = Join-Path $ProjectDir "flight_manager.py"
$LogDir = Join-Path $ProjectDir "logs"

# البحث عن Python
$PythonPath = $null
$PossiblePaths = @(
    "python",
    "python3",
    "C:\Python310\python.exe",
    "C:\Python311\python.exe",
    "C:\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)

foreach ($path in $PossiblePaths) {
    try {
        $result = & $path --version 2>&1
        if ($result -match "Python") {
            $PythonPath = $path
            break
        }
    } catch {
        continue
    }
}

if (-not $PythonPath) {
    Write-Host "❌ خطأ: لم يتم العثور على Python" -ForegroundColor Red
    Write-Host "   قم بتثبيت Python من: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# إنشاء مجلد السجلات
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

Write-Host "📁 معلومات المسارات:" -ForegroundColor Green
Write-Host "   - مسار المشروع: $ProjectDir"
Write-Host "   - مسار Python: $PythonPath"
Write-Host "   - مسار السكريبت: $ScriptPath"
Write-Host "   - مسار السجلات: $LogDir"
Write-Host ""

# التحقق من وجود السكريبت
if (-not (Test-Path $ScriptPath)) {
    Write-Host "❌ خطأ: flight_manager.py غير موجود في $ProjectDir" -ForegroundColor Red
    exit 1
}

# اختيار الجدولة
Write-Host "⏱️  اختر فترة التحديث:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1) كل 15 دقيقة"
Write-Host "  2) كل 30 دقيقة (موصى به)"
Write-Host "  3) كل ساعة"
Write-Host "  4) كل 3 ساعات"
Write-Host "  5) كل 6 ساعات"
Write-Host "  6) يومياً عند الساعة 6 صباحاً"
Write-Host ""
$choice = Read-Host "اختر (1-6)"

$TaskName = "MuscatFlightsAutoUpdate"
$Description = "التحديث التلقائي لرحلات مطار مسقط"

# حذف المهمة القديمة إن وجدت
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host ""
    Write-Host "⚠️  يوجد بالفعل مهمة بنفس الاسم" -ForegroundColor Yellow
    $replace = Read-Host "هل تريد استبدالها؟ (y/n)"
    
    if ($replace -ne "y" -and $replace -ne "Y") {
        Write-Host "❌ تم الإلغاء" -ForegroundColor Red
        exit 0
    }
    
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✅ تم حذف المهمة القديمة" -ForegroundColor Green
}

# إنشاء الإجراء
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $ProjectDir

# إنشاء المحفز حسب الاختيار
switch ($choice) {
    "1" {
        $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration ([TimeSpan]::MaxValue)
        $Description += " - كل 15 دقيقة"
    }
    "2" {
        $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::MaxValue)
        $Description += " - كل 30 دقيقة"
    }
    "3" {
        $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)
        $Description += " - كل ساعة"
    }
    "4" {
        $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 3) -RepetitionDuration ([TimeSpan]::MaxValue)
        $Description += " - كل 3 ساعات"
    }
    "5" {
        $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration ([TimeSpan]::MaxValue)
        $Description += " - كل 6 ساعات"
    }
    "6" {
        $Trigger = New-ScheduledTaskTrigger -Daily -At 6am
        $Description += " - يومياً عند 6 صباحاً"
    }
    default {
        Write-Host "❌ اختيار غير صحيح" -ForegroundColor Red
        exit 1
    }
}

# إنشاد الإعدادات
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# تسجيل المهمة
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description $Description `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -User $env:USERNAME `
    -RunLevel Highest | Out-Null

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                 ✅ تم الإعداد بنجاح!                     ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 تفاصيل المهمة:" -ForegroundColor Cyan
Write-Host "   - الاسم: $TaskName"
Write-Host "   - الوصف: $Description"
Write-Host ""
Write-Host "📝 أوامر مفيدة:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   عرض حالة المهمة:"
Write-Host "   > Get-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "   تشغيل المهمة يدوياً:"
Write-Host "   > Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "   حذف المهمة:"
Write-Host "   > Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host ""
Write-Host "   فتح Task Scheduler:"
Write-Host "   > taskschd.msc"
Write-Host ""
Write-Host "💡 نصيحة: يمكنك إدارة المهمة من Task Scheduler GUI" -ForegroundColor Green
Write-Host "   اضغط Win+R واكتب: taskschd.msc" -ForegroundColor Green
Write-Host ""

# اختبار تشغيل يدوي
Write-Host "🧪 هل تريد تشغيل اختبار الآن؟ (y/n): " -NoNewline -ForegroundColor Yellow
$test = Read-Host

if ($test -eq "y" -or $test -eq "Y") {
    Write-Host ""
    Write-Host "🚀 جاري التشغيل..." -ForegroundColor Cyan
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "✅ تم بدء التشغيل - تحقق من مجلد flight_data بعد دقيقة" -ForegroundColor Green
}

Write-Host ""
Write-Host "اضغط أي زر للخروج..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
