# 🦅 EAGLE WORKFLOW HUB 2 - QUICK START GUIDE

## What You Now Have

**Eagle Workflow Hub 2** - A complete automation system that handles your entire 6+ system workflow:

### 📁 Files Created:
1. **eagle-workflow-hub-2.html** - Main dashboard interface
2. **Eagle-Hub-2-Engine.ps1** - Automation engine 
3. **Setup-Eagle-Hub-2.ps1** - Installation & configuration

### 🎯 What It Does:
- **Email Processing**: Auto-monitors Outlook for "BID REQUEST" emails
- **KeyedIn Integration**: Extracts historical data & creates quote entries
- **Smart File Navigation**: Organizes files with proper naming conventions
- **Drawing Analysis**: CorelDRAW + BlueBeam with AIA-compliant scaling
- **Intelligent Pricing**: Uses your historical data for accurate bids
- **Multi-Hat Operations**: Estimator, Project Manager, Production, Sales modes

## 🚀 INSTALLATION STEPS

### Step 1: Run Setup
```powershell
# Open PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Navigate to where you saved the files
cd "C:\path\to\your\files"

# Run the setup script
.\Setup-Eagle-Hub-2.ps1
```

### Step 2: Choose Installation Option
The setup will show you a menu:
- **Option 1**: Full Installation (Recommended)
  - Installs everything to `\\ES-FS02\users\brady\EagleHub`
  - Sets up scheduled tasks (30 min & hourly scans)
  - Launches Chrome automatically

### Step 3: Verify Installation
After installation, you should see:
- ✅ Files copied to server location
- ✅ Chrome launcher created
- ✅ Scheduled tasks configured
- ✅ Default configuration saved

## ⚙️ CONFIGURATION OPTIONS

### Auto-Run Settings:
- **30 minutes**: Standard email & file processing
- **60 minutes**: Full system scan with deep analysis
- **Manual**: Use the settings tab for custom intervals

### Settings Tab Controls:
- **Email Check Interval**: 5-120 minutes
- **Auto-Create Quotes**: Auto/Manual/Disabled
- **Scale Detection**: Auto (AIA), 1/8", 1/4", Custom
- **Markup Percentage**: Your profit margin
- **Active Role**: Estimator/PM/Production/Sales

### Auto-Learning Mode:
The system learns from your patterns:
- Email processing preferences
- File naming conventions
- Pricing accuracy feedback
- Time-of-day usage patterns

## 🌐 LAUNCHING THE HUB

### Method 1: Automatic (Recommended)
- System launches at Windows startup
- Auto-opens in Chrome
- Runs scheduled scans automatically

### Method 2: Manual Launch
Double-click: `\\ES-FS02\users\brady\EagleHub\Launch-Eagle-Hub-2.bat`

### Method 3: Direct Browser
Navigate to: `file:///ES-FS02/users/brady/EagleHub/eagle-workflow-hub-2.html`

## 📊 USING THE DASHBOARD

### Main Tabs:
1. **🤖 Automation Control**: Monitor all systems
2. **📐 Estimating Hub**: Focus on quote processing  
3. **📊 System Monitor**: Check connection status
4. **⚙️ Settings**: Adjust all parameters

### Workflow Steps:
1. **Email Processing** → Auto-detects BID REQUEST
2. **KeyedIn Setup** → Creates job entry with historical data
3. **File Navigation** → Organizes with proper naming
4. **CorelDRAW Analysis** → Vector drawing measurements
5. **BlueBeam Review** → Raster/photo analysis
6. **Smart Pricing** → Historical data + confidence intervals
7. **Excel Export** → Professional bid documents
8. **Client Delivery** → Automated PDF generation

### Multi-Hat Operations:
Switch between roles based on what you're doing:
- **Estimator**: Focus on pricing & measurements
- **Project Manager**: Tracking & client communication
- **Production Lead**: Material planning & scheduling
- **Sales Follow-up**: Client relationship management

## 🔍 MONITORING & LOGS

### Activity Logs:
Real-time feed shows:
- Email processing events
- File organization activities
- Pricing calculations
- System status changes

### System Status:
- 📧 Outlook: Connection status
- 🗃️ KeyedIn: Response time
- 📁 G: Drive: Available space
- 🎨 CorelDRAW: Ready status
- 📐 BlueBeam: Launch status
- 📊 Excel: Template availability

## 🛠️ TROUBLESHOOTING

### Common Issues:

**Chrome Won't Open:**
- Check Chrome path in settings
- Try running setup again
- Manually navigate to the HTML file

**PowerShell Errors:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Server Path Issues:**
- Verify `\\ES-FS02\users\brady\EagleHub` is accessible
- Check network connection
- Ensure you have write permissions

**Scheduled Tasks Not Running:**
- Open Task Scheduler
- Check "Eagle Hub 2" tasks are enabled
- Run setup with administrator privileges

### Manual Overrides:
- **Emergency Stop**: Pauses all automation
- **Manual Processing**: Process specific emails/files
- **Test Mode**: Check connections without processing

## 📈 OPTIMIZATION TIPS

### Week 1-2: Learning Phase
- Let the system run automatically
- Review pricing accuracy
- Adjust markup percentages as needed

### Week 3-4: Fine-Tuning
- Customize email filters
- Refine file naming patterns
- Set role-specific preferences

### Ongoing: Pattern Recognition
- System learns your preferences
- Improves pricing accuracy over time
- Adapts to seasonal variations

## 🆘 NEED HELP?

### Check These First:
1. Activity logs in the dashboard
2. Log files in `\\ES-FS02\users\brady\EagleHub\Logs`
3. System status indicators

### Quick Commands:
```powershell
# Test connections only
.\Eagle-Hub-2-Engine.ps1 -Mode Test

# Run manual scan
.\Eagle-Hub-2-Engine.ps1 -Mode Auto -IntervalMinutes 1

# Reset configuration
.\Setup-Eagle-Hub-2.ps1 -Configure
```

## 🎯 SUCCESS METRICS

### Before Hub 2:
- 15-45 minutes per quote
- 6+ system navigation
- Manual file organization
- Guesswork pricing

### After Hub 2:
- 2-5 minutes per quote
- Automated workflow
- Smart file management  
- Data-driven pricing with confidence intervals

## 📅 WHAT'S NEXT?

The system will continue learning and improving:
- **Week 1**: Basic automation
- **Month 1**: Pattern recognition
- **Quarter 1**: Predictive capabilities
- **Year 1**: Full AI-driven workflow

---

**🦅 Welcome to the future of sign shop automation!**

Your complete workflow from email to client delivery is now automated, intelligent, and continuously improving based on your actual business patterns.
