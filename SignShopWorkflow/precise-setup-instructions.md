# **PRECISE PROJECT SETUP INSTRUCTIONS - COMPLETE VERSION**
## **Step-by-Step Configuration for Sign Shop Workflow Continuation**

---

## **STEP 1: SAVE ALL ARTIFACTS NOW**

### **1.1 Create Base Folder**
```
Create: C:\Scripts\SignShopWorkflow\
```

### **1.2 Save These Files**
1. Click **⬇️** on "Complete Sign Shop Workflow Package" → Save as: `Complete_Workflow_Documentation.md`
2. Click **⬇️** on "Workflow Documentation Status" → Save as: `Current_Status_Detailed.md`
3. Click **⬇️** on "Sign Shop Workflow Automation" → Save as: `Workflow_Automation_Code.py`
4. Click **⬇️** on "Sign Shop Workflow Utilities" → Save as: `Workflow_Utilities.py`
5. Click **⬇️** on THIS FILE → Save as: `Setup_Instructions_Complete.md`

### **1.3 Save This Entire Conversation**
1. Select all in this chat window (Ctrl+A)
2. Copy (Ctrl+C)
3. Open Notepad or Word
4. Paste (Ctrl+V)
5. Save as: `C:\Scripts\SignShopWorkflow\Full_Discovery_Session.docx`

**Why**: The conversation has 10x more detail than any summary

---

## **STEP 2: CREATE CLAUDE PROJECT**

### **2.1 Navigate to Projects**
1. Go to: `https://claude.ai`
2. Log in
3. Find "Projects" in sidebar
4. Click "Create Project" or "+ New Project"

### **2.2 Configure Project**
- **Name**: `Sign Shop Estimating Workflow`
- **Description**: `Real-world documentation of sign shop quote estimation process (15-45 min/quote)`

### **2.3 Critical Project Settings**
Look for project type or behavior settings and select:
- Technical Documentation
- Process Documentation
- Step-by-Step Instructions
- Real-World Application

---

## **STEP 3: ADD PROJECT KNOWLEDGE**

### **3.1 Upload Primary Documentation**
1. Click "Add Knowledge" in project
2. Upload: `Complete_Workflow_Documentation.md`
3. Wait for processing
4. Upload: `Current_Status_Detailed.md`

### **3.2 Add Code Files**
1. Upload: `Workflow_Automation_Code.py`
2. Upload: `Workflow_Utilities.py`

### **3.3 Add Context Files**
1. Create: `Key_Context.txt` with:

```
CRITICAL CONTEXT FOR SIGN SHOP WORKFLOW
========================================
- Workflow user: Brady (estimator)
- Total time per quote: 15-45 minutes
- Current status: 60-70% documented
- Where we stopped: CorelDRAW file open, zoomed out
- Next task: Document scale verification

KEY FACTS:
- Email starts in Outlook BID REQUEST folders
- KeyedIn is LEGACY with NO API
- Multiple popup windows open simultaneously
- G: drive files are "kind of a mess"
- Scales are NEVER 1:1
- Designer CRN saves everything in one file
- Nagle Signs always sends raster images

CRITICAL CORRECTIONS MADE:
- Email is the starting point (not KeyedIn)
- All salesperson folders equal priority
- Must verify scale even with "accurate" designers
- File selection requires finding CORRECT version
```

2. Upload this file to project

---

## **STEP 4: SET PROJECT INSTRUCTIONS**

### **4.1 Find Project Instructions Section**
Look for:
- "Custom Instructions"
- "Project Instructions"
- "Context"
- "System Prompt"

### **4.2 Paste EXACTLY This Text**

```
I am Brady, documenting my real-world sign shop estimation workflow. This is an active production system I use daily.

CURRENT STATUS:
- 60-70% documented
- Stopped at: Valley Church file (0725-39657.cdr) open in CorelDRAW, zoomed out
- Can see: Multiple versions, BRADY TAKEOFF section, circled final version
- Next: Document scale verification (22" actual measures 5.5" on screen)

CRITICAL RULES:
1. This is MY ACTUAL workflow - no theoretical additions
2. Email → KeyedIn → Files → CorelDRAW/Bluebeam → Excel
3. 15-45 minutes per quote is the target
4. KeyedIn has NO API - browser only
5. Everything I show you is factual
6. When I correct something, update immediately

TECHNICAL CONTEXT:
- Using Playwright for browser automation (not Selenium)
- G: drive organized alphabetically by customer
- Quote numbers are 5 digits (30000-99999)
- Only "BID REQUEST" status needs estimation
- Scale is NEVER 1:1, always requires verification

DO NOT:
- Add features I haven't shown
- Assume workflow steps
- Optimize unless I ask
- Skip the messy reality
```

---

## **STEP 5: CREATE PROJECT FOLDER STRUCTURE**

### **5.1 Complete Folder Setup**
```
C:\Scripts\SignShopWorkflow\
├── Documentation\
│   ├── Complete_Workflow_Documentation.md
│   ├── Current_Status_Detailed.md
│   ├── Full_Discovery_Session.docx
│   └── Key_Context.txt
├── Code\
│   ├── Workflow_Automation_Code.py
│   ├── Workflow_Utilities.py
│   └── requirements.txt
├── Screenshots\
│   └── Screenshot_Descriptions.txt
└── Session_Backups\
    └── Session_1_[Date].docx
```

### **5.2 Create requirements.txt**
```
playwright==1.35.0
python-dotenv==1.0.0
pywin32==306
pandas==2.0.3
openpyxl==3.1.2
pytest==7.4.0
```

### **5.3 Create .env File**
```
KEYEDIN_USERNAME=your_username_here
KEYEDIN_PASSWORD=your_password_here
```

---

## **STEP 6: TEST PROJECT CONFIGURATION**

### **6.1 Start New Chat in Project**
Type EXACTLY:
```
Show me the current status of the sign shop workflow documentation. Where exactly did we stop?
```

### **6.2 Verify Response Contains ALL**
- [ ] "Valley Church file open in CorelDRAW"
- [ ] "Zoomed out showing multiple versions"
- [ ] "BRADY TAKEOFF section visible"
- [ ] "22 inches height"
- [ ] "Next: scale verification"

### **6.3 If Missing Context**
Add clarification:
```
Check the project knowledge. We stopped with file 0725-39657.cdr open, zoomed out in CorelDRAW. The drawing shows 22" but measures 5.5" on screen.
```

---

## **STEP 7: CONTINUATION PROMPTS**

### **7.1 Primary Continuation (When Ready)**
```
Continue documenting my sign shop workflow. Current state: Valley Church file (0725-39657.cdr) is open in CorelDRAW, zoomed out showing all versions. The circled version shows 22" height.

Task: Document my scale verification process. When I measure the 22" text with CorelDRAW's ruler, it shows 5.5" on screen. Walk me through documenting this scale calculation and what I do next.
```

### **7.2 If Context Seems Lost**
```
We're documenting my ACTUAL sign shop workflow. I'm Brady. We're at the CorelDRAW scale verification step. The file is open and zoomed out. Check the project knowledge for full context - we've documented 60-70% already.
```

### **7.3 For Specific Clarifications**
```
In my workflow, CRN is the designer who created this file. I'm Brady doing the estimation. This is the real process I use daily, taking 15-45 minutes per quote.
```

---

## **STEP 8: VALIDATION CHECKLIST**

### **8.1 Project Setup**
- [ ] Project created and named correctly
- [ ] All 5 files uploaded to project
- [ ] Project instructions pasted exactly
- [ ] Folder structure created locally
- [ ] .env file created with credentials

### **8.2 Context Verification**
- [ ] Test prompt returns correct status
- [ ] Mentions Valley Church specifically
- [ ] Identifies scale verification as next step
- [ ] Remembers 22" → 5.5" measurement

### **8.3 File Backup**
- [ ] All artifacts downloaded
- [ ] Full conversation saved
- [ ] Folder structure verified
- [ ] requirements.txt created

---

## **STEP 9: TROUBLESHOOTING GUIDE**

### **If AI Adds Features You Didn't Show**
Say: "Stop. I didn't show you that. Only document what I actually demonstrated."

### **If Workflow Order Is Wrong**
Say: "Check the workflow order: Email → KeyedIn → Files → CorelDRAW. We're at the CorelDRAW step."

### **If Wrong Software Mentioned**
Say: "We use Playwright, not Selenium. KeyedIn has no API. CorelDRAW 2021 for vectors."

### **If Scale Assumptions Made**
Say: "Scale is NEVER 1:1. The drawing shows 22 inches but measures 5.5 inches on screen."

### **If File Selection Confused**
Say: "The file is already open. We selected 0725-39657.cdr from the messy Valley Church folder."

---

## **STEP 10: QUICK REFERENCE CARD**

### **Create: C:\Scripts\SignShopWorkflow\Quick_Reference.txt**

```
SIGN SHOP WORKFLOW QUICK REFERENCE
==================================
Current Session: 60-70% complete
Stopped At: CorelDRAW scale verification

Key People:
- Brady (you - estimator)
- CRN (designer)
- Jeff, Joe, Rich (salespeople)
- Mike E (retired)

Key Numbers:
- Quote: 39657 (Valley Church)
- Drawing: 22" height
- Measured: 5.5" on screen
- Scale Factor: 4x (to calculate)

Key Software:
- Outlook → KeyedIn → CorelDRAW/Bluebeam
- NO APIs - all browser/desktop

Key Phrases:
- "BID REQUEST" (only status that matters)
- "kind of a mess" (G: drive files)
- "MAKE SURE YOURE GRABBING...CORRECT ONE"
- "pretty spot on with scaling" (CRN)

Next Steps:
1. Document scale calculation (22÷5.5=4)
2. Show measurement extraction
3. Document BRADY TAKEOFF process
```

---

## **SUCCESS CRITERIA**

You'll know setup is complete when:
1. ✓ All files saved locally
2. ✓ Claude project shows correct context
3. ✓ Test prompt returns accurate status
4. ✓ Folder structure organized
5. ✓ Can continue exactly where we left off

---

## **FINAL REMINDERS**

1. **Save the full conversation** - It has details no summary captures
2. **Use exact prompts** - Don't paraphrase
3. **Correct immediately** - When AI assumes something wrong
4. **Time matters** - 15-45 minutes is real constraint
5. **This is production** - Not theoretical

---

**Setup complete! You're ready to continue documenting the scale verification process.**

---

## **STEP 1: SAVE CURRENT ARTIFACTS**

### **1.1 Save the Complete Package**
1. Click the **⬇️ download button** on the "Complete Sign Shop Workflow Package" artifact
2. Save as: `Sign_Shop_Complete_Workflow_Package.md`
3. Create folder: `C:\SignShopWorkflow\`
4. Place file in folder

### **1.2 Save This Instruction Set**
1. Click the **⬇️ download button** on THIS artifact
2. Save as: `Setup_Instructions.md`
3. Place in same folder

---

## **STEP 2: CREATE CLAUDE PROJECT**

### **2.1 Access Projects**
1. Open browser
2. Navigate to: `https://claude.ai`
3. Log in if needed
4. Look for **"Projects"** in left sidebar
   - If not visible, click your profile icon
   - Select "Projects" from menu

### **2.2 Create New Project**
1. Click **"Create Project"** or **"+ New Project"**
2. **Project Name**: `Sign Shop Estimating Workflow`
3. **Description**: `Documenting and automating sign shop quote estimation process from email to final pricing`
4. Click **"Create"**

---

## **STEP 3: CONFIGURE PROJECT KNOWLEDGE**

### **3.1 Upload Documentation**
1. In project, click **"Add Knowledge"** or **"Upload"**
2. Select: `Sign_Shop_Complete_Workflow_Package.md`
3. Wait for upload confirmation

### **3.2 Add Project Instructions**
1. Find **"Project Instructions"** or **"Custom Instructions"** section
2. Copy and paste EXACTLY:

```
I am documenting my sign shop estimation workflow for quotes. This is a real-world process taking 15-45 minutes per quote.

CURRENT STATUS: 60-70% documented. We have completed documentation from Outlook email discovery through KeyedIn CRM navigation to opening files in CorelDRAW. We stopped with Valley Church file (0725-39657.cdr) open in CorelDRAW, zoomed out showing multiple versions.

CONTEXT:
- I am Brady (the estimator)
- Using actual production systems
- KeyedIn is legacy with NO API (browser only)
- Workflow: Email → KeyedIn → G: Drive → CorelDRAW/Bluebeam
- Everything is factual, no assumptions

NEXT TASK: Document scale verification and measurement extraction in CorelDRAW

KEY FACTS:
- Scales are NEVER 1:1
- Designer CRN usually accurate
- Quote numbers are 5 digits
- Only process "BID REQUEST" status
- G: drive organized alphabetically by customer
```

---

## **STEP 4: TEST PROJECT SETUP**

### **4.1 Start New Conversation in Project**
1. Click **"New Chat"** within the project
2. Type this test message:

```
What is the current status of my workflow documentation and where exactly did we stop?
```

### **4.2 Verify Response Contains**
- [ ] Mentions 60-70% complete
- [ ] References Valley Church file open
- [ ] Mentions CorelDRAW zoomed out
- [ ] Identifies scale verification as next step

---

## **STEP 5: CONTINUATION SETUP**

### **5.1 Primary Continuation Prompt**
When ready to continue documenting, use EXACTLY:

```
I need to continue documenting my sign shop workflow. We stopped with the Valley Church CorelDRAW file (0725-39657.cdr) open and zoomed out. I can see multiple versions, the BRADY TAKEOFF section, and the circled final version.

Next step: Document how I verify scale and extract measurements.

Context: The drawing shows 22" height, but when I measure on screen it's 5.5". Show me how to document this scale verification process.
```

### **5.2 If Context Is Lost**
If the AI seems confused, add:

```
Check the project knowledge. We're documenting a real sign shop estimation workflow. I'm at the CorelDRAW measurement phase. The complete workflow goes: Email → KeyedIn → File System → CorelDRAW/Bluebeam → Excel pricing.
```

---

## **STEP 6: SCREENSHOT DOCUMENTATION**

### **6.1 Screenshot Reference (Text Descriptions)**
Since screenshots were only pasted in chat, create file:
`C:\Scripts\SignShopWorkflow\Screenshot_Descriptions.txt`

Copy EXACTLY:

```
SCREENSHOT DESCRIPTIONS FROM WORKFLOW SESSION
=============================================

1. OUTLOOK FOLDERS
- Shows BID REQUEST folder in folder tree
- Subfolders: Jeff, Joe, Rich, Mike E
- Email example with quote numbers visible

2. KEYEDIN DASHBOARD  
- Dark gray left menu (#505050)
- CRM menu item visible
- Widgets show "No Tasks currently assigned"

3. CONTACT MANAGEMENT SEARCH
- Dropdown shows "Quote Number" selected
- Empty search textbox
- Go button to the right

4. QUOTE LIST (NORTHWESTERN MUTUAL)
- Account: 016545
- Shows multiple quotes
- Status column shows: BID REQUEST, BID COMPLETED
- Quote 38092 has SO# 12101 but changed mind

5. QUOTE DETAIL (VALLEY CHURCH #39657)
- Three tabs: Description, Construction, Attachments
- Shows PDF attachment

6. G: DRIVE FILE MESS
- Path: G:\V\Valley Church\
- Many files: different dates (0624, 0625, 0725)
- Target file: Valley Church Halo Flange Letters Front Elev 0725-39657.cdr

7. CORELDRAW OPEN DIALOG
- Navigating to correct file
- Shows multiple versions

8. CORELDRAW ZOOMED OUT
- Multiple versions visible
- BRADY TAKEOFF section
- Circled final version
- Photos of building
- Scale note: 1.83' × 13.6' = 24.9 SQ FT
```

### **6.2 Add This Description File to Project**
1. In Claude Project, click **"Add Knowledge"**
2. Upload: `Screenshot_Descriptions.txt`

---

## **STEP 7: FAILSAFE RECOVERY**

### **7.1 If Project Fails to Load Context**
Create file: `C:\SignShopWorkflow\RECOVERY_CONTEXT.txt`

```
SIGN SHOP WORKFLOW RECOVERY CONTEXT
===================================
Username: Brady (estimator)
Current Phase: CorelDRAW measurement documentation
Completed: Email → KeyedIn → File navigation
Active: Valley Church quote 39657
File: G:\V\Valley Church\Valley Church Halo Flange Letters Front Elev 0725-39657.cdr
Status: File open, zoomed out, ready for scale verification
Next: Measure 5.5" on screen = 22" actual, calculate scale factor
```

### **7.2 Environment Variables**
Create: `C:\SignShopWorkflow\.env`

```
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
KEYEDIN_URL=https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START
G_DRIVE_PATH=G:\
CORELDRAW_PATH=C:\Program Files\Corel\CorelDRAW Graphics Suite 2021\Programs64\CorelDRW.exe
BLUEBEAM_PATH=C:\Program Files\Bluebeam Software\Bluebeam Revu\Revu.exe
```

---

## **STEP 8: VALIDATION CHECKLIST**

Before considering setup complete, verify:

- [ ] Project created and named correctly
- [ ] Complete workflow package uploaded
- [ ] Project instructions pasted exactly
- [ ] Test message returns correct context
- [ ] Folder structure created
- [ ] Screenshots organized (if available)
- [ ] Recovery context file created
- [ ] Environment variables set

---

## **STEP 9: BACKUP PROTOCOL**

### **9.1 Local Backup**
Every session, save:
1. Updated workflow documentation
2. New code artifacts
3. Session transcript

### **9.2 Naming Convention**
```
SignShop_Workflow_v[X]_YYYYMMDD.md
SignShop_Code_v[X]_YYYYMMDD.py
Session_[X]_YYYYMMDD.txt
```

---

## **STEP 10: NEXT SESSION QUICKSTART**

### **10.1 Open Project**
1. Go to claude.ai
2. Select "Sign Shop Estimating Workflow" project
3. Click "New Chat"

### **10.2 Paste Continuation Prompt**
Use the exact prompt from Step 5.1

### **10.3 Verify Context Loaded**
Confirm AI mentions:
- Valley Church
- CorelDRAW
- Scale verification
- 22" actual vs 5.5" measured

### **10.4 Continue Documentation**
Pick up exactly where you left off

---

## **CRITICAL REMINDERS**

1. **NO ASSUMPTIONS** - Everything documented is factual
2. **REAL SYSTEMS** - Not theoretical, actual production
3. **YOUR WORKFLOW** - Not generic, your specific process
4. **TIME MATTERS** - 15-45 minutes per quote is the target
5. **SCALE CRITICAL** - Never 1:1, always verify

---

## **TROUBLESHOOTING**

### **If AI Makes Assumptions**
Say: "Stop. Check the project knowledge. Only document what I actually show you."

### **If Context Is Wrong**
Say: "We're at the CorelDRAW measurement phase. File is open and zoomed out. Check the workflow status in project knowledge."

### **If Wrong Software Mentioned**
Say: "We use Playwright for browser automation, not Selenium. KeyedIn has no API."

---

**This completes the precise setup instructions. Save this document and follow exactly.**