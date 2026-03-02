# SignX Estimating System: User Manual & Standard Operating Procedure
**Date:** March 2026
**Version:** 1.0 (Unified Release)

## What is SignX?
SignX is your new, automated estimating and engineering tool. It replaces the old AbcEng.exe program with modern, up-to-date math while keeping the "instant estimate" feel you are used to. 

It does three main things:
1. **Estimates Labor:** Calculates exactly how many hours it takes to design, build, paint, and install a sign based on 22 years of your actual shop data.
2. **Engineers the Structure:** Automatically runs the math (ASCE 7-22 wind codes) to tell you what size steel pole and what size concrete footing you need so the sign doesn't blow over.
3. **Builds the Parts List (BOM):** Creates a list of exactly what materials you need to order, using your real Eagle Sign Co. part numbers (like 203-0100 for Aluminum Angle).

---

## Standard Operating Procedure (SOP)

### How to Run an Estimate
1. **Open the Dashboard:** Double-click the file located at Desktop\SignX\SignX-Dashboard\index.html. This will open the user interface in your web browser.
2. **Start the Engine:** Ensure the backend "brain" is running. Open a terminal and run python C:\Users\Brady.EAGLE\Desktop\SignX\signx-takeoff\app.py.
3. **Enter Your Data:**
   - **Sign Type:** Choose Pylon, Building, or Cabinet.
   - **Construction Method:** Tell the system *how* you are building it (e.g., Stick Build, 7" ABC Extrusion, or the new LED Thin Frame).
   - **Dimensions:** Enter the Square Footage and the Depth.
4. **Calculate:** Click the blue "Calculate Takeoff" button.

### Understanding the Results
- **Total Labor:** The total man-hours expected for the shop to build the sign.
- **Crew Install:** The specific hours required for the field crew.
- **Bill of Materials:** A bulleted list of the required steel, concrete, and extrusions. *If a part number doesn't exist in your live Inventory List, the system will show a yellow warning.*

### Generating the Engineering Report
If you need a physical printout for your records or the shop floor, the system automatically generates a 4-page PDF. This PDF contains:
1. **Cover Page:** Project name and Eagle Sign Co. branding.
2. **Elevation Data:** The size and height of the sign.
3. **Engineering Summary:** The wind pressure (qz), the exact pole you should order from stock, and the Cubic Yards (CY) of concrete needed for the truck.
4. **General Notes:** Standard building codes for your reference.

---

## Troubleshooting
- **"Inventory List.csv not found":** The system checks your real inventory to ensure part numbers are valid. Make sure Inventory List.csv is located in your Eagle Data\BOT TRAINING\Eagle Data\ folder.
- **Network Error / Failed to Fetch:** The Dashboard cannot talk to the Engine. Make sure you ran the pp.py command (Step 2 above) and leave that black terminal window open while you work.
