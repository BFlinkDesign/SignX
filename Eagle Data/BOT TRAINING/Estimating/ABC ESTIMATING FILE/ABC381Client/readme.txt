Now serial number is in the "Serial_Number.txt" file as was required.

When user runing an application, application will ask login name and password.

Login name:a
Password:

No password required. To define a password, use ABC password manager program.
Only user which have administrator rights can login in this application.
User 'a' have administrator rights.

---------------------------------------------------------------------------------------------

What's new in version 3.8.1

spr#10001BJT
Improved installation labor calculation When creating an Installation Only estimate, for installing metal letters with multiple lines of copy.

spr#10014
Changed wording "Maintenance" into "Service/Install 2" at the "Miscellaneous" screens.

spr#10016
Fixed to include painting materials for the estimates of Channel Letters (with multiple lines of copy and a border/logo) on a deck cabinet.

spr#10017
Fixed to include crating materials for the estimates of Channel Letters (multiple lines of copy) on a deck cabinet. Improved crating labor
calculation.

---------------------------------------------------------------------------------------------
Changes in version 3.8.0

spr#10015BJT
Now overtime hours are added to the Work In Progress and the Completed Job reports.

---------------------------------------------------------------------------------------------
Changes in version 3.7.9

spr#09026
Improved labor factors import. This improvement allows preserver labor factors values from old version and preserver default values of new labor factors introduced in the new version. But this solution has several exceptions when this will not work:

	Labor’s selectors count has been changed in the new version; In this case such labor will be omitted from update. 
	Labor factor selection order has been changed in the new version; In this case such labor will be omitted from update.


---------------------------------------------------------------------------------------------
Changes in version 3.7.8

spr#09019
Improved file reading. Now it doesn't lock a inventory file for a long, when enter inventory at the Miscellaneous Items screens in the estimating module.

spr#09020
Improved customer cards. Now created customer card appends paperclip info from appropriate pending customer car, when closing job.

spr#09022
Fixed calculations for Pattern Paper and Neon Pattern Paper materials to maintain correct amount. 

spr#09024
Improved production schedule report for Shop Orders. Now this report contains GL expense code (labor expense code) information.

spr#09025
Improved customer name transfer from general information screen to printout selection screen. Added customer name and phone field for job location information at the general information screen.

Also, updated labor factors.

---------------------------------------------------------------------------------------------
Changes in version 3.7.7


Updated proposal script.

---------------------------------------------------------------------------------------------
Changes in version 3.7.6

spr#09002
Improved proposal number generating for client/server application.

spr#09003
Removed comma between state and zip code in the Proposal and Detailed report. Removed additional blank space from customer address data in the detailed report and proposals.

spr#09006
Improved "ship to" address management at the "shipping to" address data screen. Now double click in the company name field will select all text, "TAB" pressing will open "Select Customer" screen, and "Enter" will allow input of any company name.
Now compony name for job location is transferried into MSBS shipping address.

spr#09007
Now taxes calculated in the Accutrack are transferried into MSBS invoice.

spr#09008
Sales person ID is added into proposals.

spr#09009
If customer data has fax number, now customer's fax number is transferried in the estimate's first screen automaticaly and formatted the same as phone number.


spr#09011
Improved distributions handling in the invoicing in case payment received would be calculated correct.
Fixed problem with deposit and additional payments. 

---------------------------------------------------------------------------------------------
Changes in version 3.7.5

spr#07037

Improved custom items handling in the "Maintenance" department. In case to separate monthly rate calculation and user added custom maintenance items, new department "Service/Installation 2" was created. Now, added custom items for maintenance are handled in this department.

---------------------------------------------------------------------------------------------
Changes in version 3.7.4

Improved pending customer cards and JO description Word document addendum creation functionality:

1. If user selected "Yes" to create word document addendum during "Detailed" or "Brief" estimate reports generation, word document for job description would be created, but not "auto saved" into "paperclip" folder. User could "save as" self that word document.

2. The same happens if user generated proposal, select "Yes" to create word document addendum, but did not checked option "Create pending customer card".
If user generates proposal and select option "Create pending customer card" - proposal is "auto saved" into "paperclip" folder and attached to appropriate pending customer card. If user selected "yes" to create word document addendum during proposal generation, word document for job description is "auto saved" into "paperclip" folder and attached to appropriate pending customer card too.

3. Disabled feature to create word document addendums for job description during Work Order writting.


---------------------------------------------------------------------------------------------
Changes in version 3.7.3

Updated sample estimates MOTEL1, UNION1, UNION4, UNION6, and UNION6A.

Fixed errors, which appear, when user selects "NO" for Job Description Word Document Addendum.
Improved pending customer cards creating functionality. After user creates pending customer card during work order writing, the button "Create/Append Pending Customer Card" will be disabled.


---------------------------------------------------------------------------------------------
Changes in version 3.7.2

spr#08003

Improved MS Word document creation functionality for long jo descriptions. Added dialog "Create Word Document Addendum for Description? (Y/N)". If user selects "YES", then a word document will be prepared for job description without checking length of it.
Also, work orders reports have been improved in case o have more room for job description.

spr#08013
Fixed problem with inventory import from "*.xlsx" files.

---------------------------------------------------------------------------------------------
Changes in version 3.7.1

Updated Engineering module version number to 3.7.1.
Updated inventory file.

spr#07038
Added new functionality, which allows for user to delete customer cards. 
Improved pending customer card insert fuctionality in case to add installation address.
Added new functionality, which allows for user automatically add "Complete Job Report" into customer card.

spr#08013
Improved pull-down list for "Files of type". Options "*.xlsx" and "All files (*.*) are added.

Improved naming of MS Word document generated for long job descriptions.

---------------------------------------------------------------------------------------------
Changes in version 3.7.0

spr#07038
Solved "data truncation" problem.

spr#07039

Added new functionality. Now custom inventory items could be inserted or removed into/from inventory database at the "Materials Update" screen. To add new inventory item press "Add New" button when appropriate department selected. Enter description, cost ant unit of measure (default is "each") for new inventory and press button "Save Changes".
Custom added inventory items can be removed. Select appropriate custom inventory item and press the button "Delete" .

spr#08003
Improved full job description printout functionality. Word document will be prepared when generating "Detail Estimate Report" or "Brief Estimate Report".
If job description does not exceeds margins of the "description" field of report, word document will not be prepared.

spr#08013
Improved inventory export/import to/from MS Excel file. Now all inventory database could be exported into MS Excel file. Fixed problems with new added, changed inventory import. Also errors checking have been improved too.

---------------------------------------------------------------------------------------------
Changes in version 3.6.9

spr#07038
Added new type of customer cards - Pending Customer Cards. If user checks option "Create Customer Card" at the final screen of estimating, then pending customer card has been created and saved in the customer cards database. Appropriate proposal number is added instead wo number.
If user creates empty job(without estimate file), when appropriate pending customer card would be created after pressing "Create/Append customer card" button at the last screen of Work Order writer ("Installation / Shipping Instructions for Work Order" screen). Appropriate WO number is used ti identify pending customer card.
If user Opens Job for Costing, appropriate pending customer card would be updated by pressing "Create/Append customer card" button at the last screen of Work Order writer, changing proposal number to appropriate WO number. Proposal number used before is added into Notes.
After closing job MO or JO customer card is created. Appropriate customer card used before is not accessable.
Pending customer cards list is available form menu "Customers -> Pending Job Customer Cards".

spr#07039
Added new functionality to insert existing inventory items into Miscellaneous screens of all departments. At the "#Department#, Miscellaneous" screen, press Tab or Enter in the "Item Description" field. The list of inventory items for selected department appears and user could insert appropriate inventory item by selecting it in the list and pressing OK button. Material Cost and Markup fields will be updated too by appropriate values.

spr#08013
Added new functionality to import/export local inventory database from/to MS Excel file.
Go to menu "Tools -> Export Inventory to Excel File". Opens dialog where user could select desired department to export. Inventory items from selected department will be exported after pressing "Export to Excel" button.
To import inventory from excel file, go to menu "Import Inventory from Excel File". File selection dialog appears and user must select appropriate excel file.
New inventroy items could be imported into local inventory database. In this case, export inventory of desired department using "Tools -> Export Inventory to Excel File". Open created excel file. Enter new inventory item's data at the end of list of inventories of department. For Example, we need to add new inventory into "Patterns / CAD" department:
The last item of this department is "D1P2 Pattern Paper". Below this item, into new line we need enter this information:
Column "Dept#" = 1 (Department ID);
Column "Part#" = D1P3 (D1 means appropriate department, P3 inventory part number, number should be increased each time new item is added);
Column "Description" = "Description of inventory item";
Column "Unit Price" = "Item price";
Column "Unit Code" = "Code of units of measure";
Column "Units" = "abbreviation of unit of measure";
Save excel file and import it from menu "Import Inventory from Excel File".

spr#07037
Improved description generation for miscelaneous item in the detailed printouts.
Restored previous functionality for "Maintainenca Only".
Improved "Open JObs report".

spr#08003
Improved printing of full job description. Currently it is printed separate in the word document.

spr#08007
Item D5P75 description was changed from ".040 Prefinished Aluminum" to ".040 Mill Finish Aluminum".
spr#08008
"Use computer estimate for Materials" is preselected by default.
Improved labor calculations in "CAD/CAM" department.

spr#08009
"Design#" is modified to "Estimate#" at the first screen of estimate.
"Contract Number" is modified to read "Proposal Number" at the last screen of estimate.
Improved field of proposal number alignment.

spr#08011
Fixed system crash at the first start up of system.

spr#08012
Improved recently used files list. "Files -> "Recent Files" pop ups MRU. It contains names of last 9 files.

spr#08018
Improved calculations for Rectangular Awnings.
Added labor for "Load for Shipping" at the woodwork department.
Improved awning sign area calculations.

Also, included newest Keylok installation program.

---------------------------------------------------------------------------------------------
Changes in version 3.6.8

spr#07037
Added "Maintenance" department into Estimate and Job Costing modules. "Maintenance" is added in the "Miscellaneous Menus Desired" screen. If this selection has been made, new screen "Maintenance, Miscellaneous" will open and acts just like the others. Estimate detail report was improved to show "Maintenance" department.Department's combo box contains "Maintenance" department in the "Enter Job Cost Data", "Material Data Entry", and "Labor Data Entry". WIP and "Closed Job" reports also were improved to have "Maintenance" department.

spr#08003
MO, JO, SO and Proposals have added additional worksheet "Full Job Description" in case to have full job description in the reports.

spr#08004
Added polycarbonate to list of materials for routed faces of channel letters. If the user selected  "Letters or Graphics" at the General Information 3 screen and then selected "Channel" at the Copy 2 screen, and then selected "Channel Letters with routed faces" at the Fabricated Letters 1, Line (x) menu, new screen would be open "Routed Plastic for Channel Letters, Line (x)" with list of new material items: .125" Acrylic;  .187" Acrylic; .250" Acrylic; .125" Polycarbonate; .150" Polycarbonate; .187" Polycarbonate. After making the correct selections, menu "Edging and Plastic Type, Line (x)". Depending on selection in this screen, appropriate labor and material items would appear in the detail report. Improved labor and materials calculation in the "Plastics" and "CAD/CAM Machine time" departments.

spr#08007
Improved "Channel Letters, Line#" and Channel Letters Depth, Line#" screens. Now user could substitute materials used for backs of channel letters and edging for channel letters.

spr#08008
Added new material items .750" Clear Acrylic; .750" White Sintra; .750" White Acrylic; 1.00" Clear Acrylic; 1.00" White Sintra; 1.00" White Acrylic in to Plastics department and appears in the screens: "Routing Materials, Line (x)", "Push-Through Material, Line(x)", and "Routed Face Material, Line (x)". Appropriate labor factors and materials in the "Plastics" and "CAD/CAM Machine time" departments were updated and appear in the detail estimate report.

spr#08009
Added auto number to proposals. Added new field for proposals number at the beginning of proposal. Changed text in cell S15 from "Design" to "Estimate".  Changed text in cell A43 from "Contract Number" to "Proposal Number". Changed text from "Design #" to "Estimate #" at the first screen of estimate.User could set initial proposal number at the "System Configuration" screen, which accessible from "System" menu.  

spr#08010
Improved Order Entry Journal. Now invoice number and ship via information appears in the Order Entry Journal.

spr#08011
Loading screen appears when application starts.

spr#08012
Add recently used files list into "File" menu. It contains names of last 5 files.

spr#08014
USB Dongle key drivers have been updated for client version.

spr#08015
Improved formatting of zip code in the JO and MO to show leading zeros.

spr#08017
"Can't read estimate file %Path% because the file is empty." Message appears when user trying to open empty estimate file.

spr#08018
"Length of Bars" field was removed form "Awning - Mansard/Rectangular/Trapezoid" screen in the estimate module. Value of this field was used to calculate area of awning frame. So, awning area calculations were improved using new logic: standard mansard use greater value of height or projection; trapezoid greater value of "Length at top" vs "length, and greater "Projection at Top" vs "Projection".

Also, inventory database has updated filter's brands.

---------------------------------------------------------------------------------------------
Changes in version 3.6.7

spr#07034
Added labor for painting cabinet when Thrif-T frame selected;

---------------------------------------------------------------------------------------------
Changes in version 3.6.6

spr#07032
Now generates illumination ballast labor for Thrif-T frames;

---------------------------------------------------------------------------------------------
Changes in version 3.6.5

spr#07007
Improved customer selection screen when user is asked to replace current customer information and press Yes button.

---------------------------------------------------------------------------------------------
Changes in version 3.6.4 

Prepared new dongle key / accutrack installation flow. Created new "splash" screen with possible option:

	Install Dongle;
	Install Accutrack;
	Read Help;
	Exit;
Now Dongle key installation is separated from Accutrack installation.

---------------------------------------------------------------------------------------------
Changes in version 3.6.3

spr#06004
Improved strut bracket materials calculation for single face frames.

spr#07007
Added customer selection screen when user is asked to replace current customer information and press Yes button.

spr#07009
Added Thrif-T labor constant and description into detailed print out.

spr#07014
Improved production schedule report and screen.

spr#07022
Improved inventory items import feature.

---------------------------------------------------------------------------------------------
Changes in version 3.6.2

spr#07007
Improved customer selection during create empty job. Now user could type a portion of customer name, press Tab key and select appropriate customer from customer's list.

spr#07009
Added new Thrif-T frame system to conventional frames.

spr#07014
Added shipping address and job site address into production schedule. 

spr#07022
Improved inventory items import feature. Now user could export inventory database before new ABC system version is installed. When new ABC system version is already installed, user could import inventory without overwriting "new added" or "changed" inventory from new installation.

---------------------------------------------------------------------------------------------
Changes in version 3.6.1

spr#07001
Fixed problem of Multiple lines of copy for internal structure material quantity. Now right quantity is generated then are multiple lines of copy.

spr#07002
Fixed. Added unit of measure description at the "Printed Graphics Process" screen.

spr#07003
Fixed installation labor missing for Awnings. Now generates right installation labor for Awnings when the height and the projection are the exact same dimension.

spr#07004
Fixed. Now generates one lamp ballasts for 425ma lighting.

spr#07005
Fixed. Now generates ballasts for 277 volt lighting.

spr#07006
Improved installation address handling.

spr#07008
Changed description "H-Divider Mount Brackets" to "Divider-Bar Mounting Brackets".

spr#07015
Improved Engineering module to work with USB dongle key.

---------------------------------------------------------------------------------------------
Changes in version 3.6.0

spr#06008
Improved menu "Knife-Cut or Printed Letters". Now menu items "Films for Printed Graphics" and "Inks for Printed Graphics" are not mutually exclusive of one another.
Improved calculations of material "Inks for Printed Graphics" in the detailed estimate.


---------------------------------------------------------------------------------------------

Changes in version 3.5.6

spr#06009
Improved installation address selection on "Create card" dialog.

spr#06014
Improved calculations for double face "Neon cabinet" selection, with light or medium internal frame.

spr#06021
Improved wording for menu for mounting Flat Cut Out letters.
Improved "Field installed" selection for acrylic plastic routing material.

---------------------------------------------------------------------------------------------
Changes in version 3.5.5

Implemented compatibility with USB Keylok device to provide security on computers equipped only with USB ports.
Changed departments rates in the dept_nm.abc file.

spr#06008
Wording and price changed for items D5P39 and D5P41.
Improved calculations of labor and materials quantities for printed graphics selections.

spr#06009
Improved installation address selection.

spr#06014
Improved calculations for "Deck Cabinet" selection, for correct amount of materials based on sign type.
Improved general description on detailed estimate.

spr#06020
New wording "Paint Routed Faces/ Routed Letters or Border/Logo" implemented at "Finishes 1" menu.

spr#06021
Implemented new feature to make labor for mounting Flat Cut Out letters to appear in the appropriate department.



---------------------------------------------------------------------------------------------
Changes in version 3.5.4

Updated people and materials costs.

spr#06008
Improved wording and calculations of labor and materials quantity for printed graphics selections.

spr#06010
Improved fax number transfer into proposal form and installation / Shipping Instructions for Work Orders screen.

spr#06012
Fixed problems in the engineering module and engineering help page.

spr#06014
IMproved calculation for selections of “Medium Framework” in combination with Neon Cabinets,  Plastic Sign Frames,  or Deck Cabinet.



---------------------------------------------------------------------------------------------
Changes in version 3.5.3

spr#06008
Converted existing Heat transfer selections to Digital Printing Capabilities.

spr#06009
Added Job Site address to estimate, orders and customer cards.

spr#06010
Added field to enter fax number at the first estimating menu.

spr#06011
Work order number is transfered into customers cards.

spr#06012
Improved engineering module to expand pipe table.

spr#06014
Added option for angles or square tubes on sheet metal cabinet framing.


---------------------------------------------------------------------------------------------
Changes in version 3.5.2

spr#06001
Improved envelop page for job and manufacture orders.

spr#06002
Improved exit rule for "divider bars" selection at the "Fabrication Extras 3" screen. Now user must enter lineal feet per face and select divider bar size.

spr#06004
Strut brakets materials included for some frame combinations.

spr#06005
Paint labor and materials included for Extruded Aluminum Deck Cabinet.

spr#06006
Improved selection for channel letters, when deck cabinet is used. Improved exit rule for deck cabinet selection at the "Sheet Metal 2" screen.

spr#06007
Improved Translucent paint materials calculation when Acrylic Border /Logos are added to paint.

---------------------------------------------------------------------------------------------
Changes in version 3.5.1

spr#05009
Fixed problem with multiple iteration of the labor factor for "Wall mount installation of deck cabinet and letters", avoided "Illegal selection for labor Metal Letters" on "Installation Only" estimates.
Furthermore, quantity provided by the user at the "Installation 4, Mount Metal Letters" screen replace auto-calculated quantity for letters that are mounted on deck cabinet.

spr#05011
Improved calculations for quantity of the backing material for routed faces with backing.

---------------------------------------------------------------------------------------------
Changes in version 3.5.0

spr#04029
Improved calculations of material quatity and labor units for "Select if tubing to be installied" 
selection at the "Illumination, Neon Copy Line #" screen. Now data for this selection is coorectly 
calculated for detail estimate.

spr#04008
Improved general estimate description by inserting "(color) LED Lihting" string(s), where illumination 
type description would appear.

spr#04009
Improved general estimate description by inserting "User provided custom material description" 
in the place the type of sheet metal skin woulds appear.

spr#04011
Improved "Pipe Hardware Only" labor units calculation for Hinge Frame Accessories. "Pole Mounting 
Brackets" labor units would appear in the Extrusions at the detailed estimated.

spr#04013
Improved envelop sheet for JO and MO. Invoice date, date completed and invoice number fields are left 
empty now. Additional fields for Permit Fee, Subcontract Fees and Taxes are added.

spr#04032
Bar code field would be empty now.

spr#05003
improved "MAINTENANCE 2" screen's exit rule for maintenance of skeleton neon.

spr#05004
Wrong iteration of sheet metal screens was removed for intricate sheet metal signs.


---------------------------------------------------------------------------------------------
Changes in version 3.4.8


******* BUG FIX list:

spr#04022
Improved Trim Cap quantity calculation on Border/Logo

spr#04023                     
Fixed Pole Cover labor calculation algorithm for Installation department

spr#04024                     
Fixed installation labor error for FCO letters exactly 24”

spr#04025                     
Improved Enamel and Polyurethane paint material quantity calculation for multiple lines of copy 
for Fabricated letters

spr#04026
Fixed Border/Logo material options bug at the Ornamentation 2, Border/Logo Materials menu

spr#04027
Fixed Border/Logo paint area quantity selection for labor calculation.

spr#04028
Improved Weed & Apply labor and material calculation, when materials quatity is less then 0.25sq. ft.

spr#04029
Improved menu path for Skeleton Neon

******* NEW FEATURES list:

spr#04008
Added LED lighting to Special Lighting menus

spr#04009
Added Custom metal materials for Sheet Metal Cabinets

spr#04010                     
Implemented wording changes to Custom Hinge Frames screen

spr#04011                     
Added feature to allow user-defined quantities at Hinge Frame Accessories Menu

spr#04013                     
Improved Work Order templates. Additional MS Excel worksheet is added to print job envelop for JO and MO work orders

spr#04032
Additional field is added to print invoice number in the work orders.

spr#04035                     
Now option "Create/Append service tracking record" defaults to "yes" at the Clse Job screen


---------------------------------------------------------------------------------------------
Changes in version 3.4.7

Fixed problem with engineering module running on Windows XP with SP2.

---------------------------------------------------------------------------------------------
Changes in version 3.4.6

spr#04003
Improved retroframes selection in the estimate module. Now retroframes  selection doesn't iterates sheet metal screens.

spr#04005
Improved Manufactoring order report. Company name field is centered.

spr#04006
Installation address appears in the Work Order, when only "Install This Order" option is selected
at the "Installation/Shipping instructions" screen.

spr#04007
Improved order entry journal. Now user is able to edit manufacturing orders just as user can under job orders.

spr#04017
Removed ability to edit/change WO Number at the "Write an Order/Open Job for Costing" dialog.

spr#04018
Improved key generation module for option "Order Writer w/ Journ & Prod Schedule". Now "Job" menu is
available for Order writing.

spr#04019
Improved functionality for the Edit Order Journals: the entered invoice amount currently will be saved.


---------------------------------------------------------------------------------------------
Changes in version 3.4.5

Updated *.src files, which have improvements in regards to sprs 03005 and 03010.

Improved spr's 03007 fixe.



---------------------------------------------------------------------------------------------
Changes in version 3.4.4

spr#03005
Improved "Trico-Plex" material calculation for "Pole Cover". Changed constant value.

spr#03009
item#1. Improved "Total Estimated Journeyman Hours" calculation on "Work In Progress" and "Work Completed" reports
item#2. Improved "Total Estimated Hours" and "Actual Journeyman Hours" comparison for "Installation department.

spr#03010
Added new possibility "Replace/Append Notes to Description" at the Detailed estimates printouts. New selections are added at the "Miscellaneous Menus Desired" screen in the estimating workflow.

---------------------------------------------------------------------------------------------
Changes in version 3.4.3 

spr#03001
Fixed Radius Corner bug with multiple iterations of lines copy or miscellaneous items.

spr#03003
Fixed problem with "Noen Tube Supports". Currently system doesn't generate "Neon Tube Supports" in combination with "Column Mounted" and "Used Pipe" unless "Neon" has been selected.

spr#03004
Improved labor calculations for Z brackets, when "Small A/Flexframe (S/F only) is used.

spr#03005
Improved "Trico-Plex" material calculation for "Pole Cover". Currently system evaluates face(s) area also.

spr#03006
Wording of labor describtion on detailed printouts improved to "Stringers for mounting" and labor factor is updated to 0.075 hours per lineal foot.

---------------------------------------------------------------------------------------------
Changes in version 3.4.2

Improved customer data loading. Now customer datbase used with Accutrack is compatable with ABC Estimate system.
---------------------------------------------------------------------------------------------
Changes in version 3.4.1

SPR#02043
Problem with customer name, when closing job and "Create/Append Service Tracking Record" options is selected, was fixed.


---------------------------------------------------------------------------------------------
Changes in version 3.4.0

SPR#02027
Improved calculations of materials for radius corner, when other then "Conventional" frame
type is selected.

SPR#02035
Improved "User Maintenance" module. "Maintenace 2" wording is changed to "System". Also, "System" user could view "Volume" and "Cumulative Volume" columns on the "Production Schedule" reports.

SPR#02038
Fixed problem with "Awnoflex" material selection when multiple lines of copy or multiple miscellaneous items exist.
Solved problem with calculation of correct amount of material when multiple lines of copy or multiple miscellaneous items exist.

SPR#02040
Fixed problem on import\export of ballasts costs.

Improved sample estimates are added in regards to better demonstrate the current system features.
---------------------------------------------------------------------------------------------
Changes in version 3.3.9

SPR#02033
Now generates labor for creating the foundation when "Used Pipe" is selected.

Also, fixed problem with 1 x 4, 2 x 4 lumber when multiple number of miscellaneous items are  entered (multiple iteration are used).
---------------------------------------------------------------------------------------------
Changes in version 3.3.7

Improved "Closed Manufactured Order Customer Cards" report.

---------------------------------------------------------------------------------------------
Changes in version 3.3.6

spr#02030
Improved Closed Job Customer Cards enabling/disabling feature. Now menu "Customer" appears only
if this functionality is included in the KeyLock/SN authentication.

spr#02019
There was made change in customer database related with multisectioned
estimates handling. Furthermore we improved installation program doesn't
overwrite the existing customer cards database. So, when you install new
ABC system without uninstalling previous version, then customer database
isn't updated. Customer database used with older versions is not
compatible with versions 4.3.6  3.3.6.

Also, Hingeable Frame Prop Hardware labor factor was updated to 0.33 in the Extrusion department.

---------------------------------------------------------------------------------------------
Changes in version 3.3.5
WO7 item#10
Improved paint labor and materials calculations for multiple lines of copy for channel 
and routed letters .

WO7 item#16
Now CAD/CAM machine time is generated for knife-cut letters with used color of sign 
face material.

spr#02019
Improved customer cards for multiple sectioned estimates.

spr#02022
Bug on "Actual Journeyman Hours" in WIP reports was fixed.

spr#02023
Estimates "File->Save As" bug fixed.

spr#02025
Bug on "Add new material" at the Job costing was fixed.

spr#02026
Installation process was improved and now customer cards data didn't lost during update 
process.
---------------------------------------------------------------------------------------------
Changes in version 3.3.4

WO7 item#16
Problem with itaretive choice to "Use Color of Sign Face Material for this line of copy" 
was fixed.

spr#02015
Problem with "Mount Routed Push-Throughs" was fixed.

spr#02012
Problem with 49" and 73" posts was fixed.

spr#01033
Improved wording of desired printout message for "Work in Progress" reports.

spr#01058
Now when user enters the same job number as already exist, new information message 
"Job with the same number already exists. Are you sure you want to overwrite existing 
job with this one?" will inform user about this.


---------------------------------------------------------------------------------------------
Changes in version 3.3.3

spr#2k185
Improved awnings installation area calculation for "Other-> Other Custom shapes" awning type.

spr#01040
Fixed problem with "End Mount/Projecting Mount".

spr#01055
Improved wording on errors messages.

spr#01056
Fixed problems described in this spr.

spr#02012
Improved post materials quantities calculations as was required. Now user could do estimates 
for small posts.

spr#02013
Improvements was made for for this spr's item#2.

spr#02015
Fixed problem with routed background and push-throughs.

spr#02017
Problems related with entering miscellaneous items was fixed.

---------------------------------------------------------------------------------------------
Changes in version 3.3.2
SPR#02004
Fixed problem related with the interrupted JO printing routine.

SPR#02002
Payment terms are transferred to invoice now.

SPR#02010
Problem with multisection materials list on the Job Shop Copy and Work In Progress Reports 
is fixed.

spr#02013
Improved Trico-Plex calculations.

item#15
Improved calculations for radius corner.

---------------------------------------------------------------------------------------------
Changes in version 3.3.0 beta4

Fixed problem with proposal generating.

Fixed spelling on the closed cards screens.

Fixed margin problems in the engineering help system

---------------------------------------------------------------------------------------------
Changes in version 3.3.0 beta3
Fixed Disable/Enalbe the Customer Cards feature.

SPR#01054DS
Accutrack program read number from SY01500, program increased note index by one write new index back to SY01500 and add note with new index.
Fixed. Program now read number from SY01500, add note with this index, increase this index and write back to SY01500.

item#16
Now "Use Color of sing face Material for line of copy" selection deselects all other selection
at the "KNIFE-CUT LETTERS, LINE #". Also, labor calculations was improved.

item#9
Now "Work in Progress" report accumulates hours on the same pay rate and doesn't creates 
separate line.
spr#02012
Estimate of Post length was improved in regards to estimate very small signs.

spr#02016
Exit rule for pipe rings for staged pipes was improved. Now user should enter mark up if 
the user selects pipe rings at the "Installation 8, Pipe Fabrication extras" screen.

spr#02058
Error/information messages text was improved to be more informative to the user.

spr fro L & S Curved frames
Labor calculations was improved.

Also, all items from the "Preliminary results from testing latest version" (date: Mon, 25,
Mar 2002) was reviewed and improved/fixed.
---------------------------------------------------------------------------------------------
Changes in version 3.3.0 beta2

item#9
Was improved work in progress report. Now report lists each different pay rate for each 
employee.

item#13
"Sheet Metal 1", "Sheet Metal 2" and "Sheet Metal Materials" screens exit rules was improved.

item#14
Labor and material calculations was improved for "Extruded Aluminum" selection under
"Choose Material for Wireways" at the "Wireway materials" screen.

item#15
Problem related with material for radius corner was fixed.

item#16
Problem with "Use Color of Sign Face Material for this line of copy" selection was fixed.

item#17
The new feature to hide dollar amounts was improved for Prduction Schedule Journal.

item#18
Notes field was moved to the "Miscellaneous" menu. Now text entry window is larger.

item#19
Menu path for Wide-Fab frames was improved.

item#20
The exit rule at the "Plastic Face Only" screen was improved.

spr#02011
Improved curved frame labor calculation for retainers.

spr#010314
Work order number field has character limit to 8.

spr#2k310
"Add amount" button was added to the "Material Entry screen".

spr#01055
Improved information and error messages.

spr#01056
Improved functionallity of "Return to First Job Cost Menu" button at the "Labor Entry screen.
Fixed problems related with shotkey and text message.

spr#02013
Fixed problem with Trico-Plex material at the Finish department.

spr#2k185
Improved awning installation area calculation.

spr for L&S Curved frames
Fixed problem related with labor for "Existing Jig" calculation.

Also, Cooley magic fluid calculations was improved. Lamps lengths checking was improved.
Engineering on-line help was updated.

---------------------------------------------------------------------------------------------
Changes in version 3.3.0 beta1

Implemented new Wish List:

item#2
Updated excel file "BoltBase.xls". Now the user could calculate bolt diameters down to 3/8 inch. Added Gusset table (file "Gusset.xls) and functionality related with this table, which provides new additional information in the result that are displayed/printable for Anchor Bolt/Base Plate portion of the engineering module. Also was updated on-line help system and added new menu item "Gusset dimensions" in the "Help" menu.

item#4
Customer feature.....

item#7
Added to the on-line help system within the Engineering Module a Chart which shows standard weights for (standard) Schedule 40 and (heavy-wall) Schedule 80 steel pipes and also a chart for square tubes that will assist the user in calculating the estimated total weight per column above grade (for all pipe stages combined). This chart is available via "Help"->"Schedule Pipes".

item#9 (SPR#158)
Added sorting  by employee ID feature to the Work in Progress report.

item#10 (SPR#159)
Fixed problem with painting routed faces on channel letters.

item#11
Repalced screen Title for "Plastics 1" menu to "Face Materials" and for "Finishes 1, Painting Faces" to "Finishes 1, Painting Specifications".

item#12
Now Plastics screens are iterative. This allow the user to estimate multiple lenses for a sign.

item#13
Modified "Sheet Metal Materials" and "Sheet Metal 2" screens. Added new selections, new labor factors and materials as was required.

item#14
Added new options at the "Wireway Materials" screen. Updated existing labor and materials calculations in regards to new options.

item#15
Modified "Extrusions, Radius Corners" screen. Updated materials calculations and inventory file in regards to costs from "radcrnr.xls" file.

item#16
Improved background color selection for knife-cut letter. Now allow use white color of sign face material for white color of line copy.

item#17
Now dollar amounts are hidden on the read-only  Product Schedule and Order Entry Journal for all user except for users who have m1 or higher security privileges.

item#18
Note field was added at the bottom in the last screen of estimate. Note appends to the end of description.

item#19
Improved algorithms for Wide Fab type frames. New screen "Steel Plates for Wide-Fab Pipe Hardware" was added to the menu path if "Wide Fabricated Frames" was selected.

item#20
Improved algorithms for Plastics 6 screen. "No Frame" option was changed to "No Mold" selection. "Quantity Faces, 20 or More" was removed.

---------------------------------------------------------------------------------------------
Changes in version 3.2.9

spr#01035
Improved calculation in the "Maintenance" department regards to spr item#8.

---------------------------------------------------------------------------------------------
Changes in version 3.2.8

spr#01035
Corrected and improved calculation in the "Maintenance" department regards to spr item#5B and item#8B.

---------------------------------------------------------------------------------------------
Changes in version 3.2.7

spr#01035
Corrected and improved calculation in the "Maintenance" department. Fixes related with spr's item#5B and item#8A and item#8B are included also.

SPR#01038
Problem with multiple iterations of labor for fabricating the "Curved Frame" in the "Extrusion" department was fixed.

SPR#01039
Problem with Woodwork department constant was fixed. Now right constant value is used from appropriate size category in the woodwork department.

SPR#01040
Missed labor factors was added for "Zero Clearance Hinge Frame" options and "Large Bleedframe" and "Small Bleedframe". Also, "Curved Frame" selection now is hidden for Zero Clearance option.

spr#01044
Error related with date change was fixed.
---------------------------------------------------------------------------------------------
Changes in version 3.2.6

spr#01033
"Work In Progress" reports with summary page generating was improved.
Also, the screen that appears now gives the user two options; 
                "Print Work In Progress Report with Summary Page" 
                "Print Work In Progress Summary Page Only"

---------------------------------------------------------------------------------------------
Changes in version 3.2.5

spr#01007
The standard error message "Illegal combination,......" will apear and prevent the user from
exiting the screen "Illumination 3, Fluorescent 2" unless they have provided valid lamp length
for 277 Volt ballast.

spr#01024
The standard error message "Illegal combination,......" will apear and prevent the user from
exiting the screen "Illumination 3, Fluorescent 2" unless they have provided valid lamp length
for standard (120 Volt) ballast.

spr#01026
Now Steel Plates are generated coresponding to frame type with the Zero Clearance Saddle & Carrier 
selection.

spr#01027
Improved "Save As" operation from menu "File". Now after choosing "Save As" new estimate are opened 
and original estimate are saved and closed.

spr#01032
Now value entered into the "Enter Additional Amount" field at the "Material Data Entry" screen is
added without pressing the "Enter" key.

spr#01033
Now both "Work In Progress" and "Completed Job" reports have Summary report.

---------------------------------------------------------------------------------------------
Changes in version 3.2.4:

spr#010122
item#1: Now trailing space is removed from the customer information when populating template
fields.
item#2: leading zeros in the zip code are imported when populating Shop Copy fields.

---------------------------------------------------------------------------------------------
Changes in version 3.2.3:

Improved system update. Now information about system users are saved when updating Accutrack
to newest version.

---------------------------------------------------------------------------------------------
Changes in version 3.2.2:

Now if a serial number with time limit is used, then system message "Accutrack time remaining
[= number of days]" appears if 30 or less days left to the expiration date. After the serial
number expires, system will show "Accturack time expired!" message and terminates.

Now user don't need to uninstall previous version of estimate system when updating to this one.
Simply, install this version to the same folder where is previous version installed. This will
save all configuration settings and Journeyman Rate and Cost. Remember, to save Labor Factors
and Inventory Costs and Names, export them before installing this version, and import them after
installation.
---------------------------------------------------------------------------------------------
Changes in version 3.2.1:

spr#247
Proposals for Lease/Rental agreements was improved. TOTAL AMOUNT OF CONTRACT is calculated using
 only 2 decimal places.

Also was updated system online help. Now Production Schedule and Order Entry Journals both will
display only three lines of job description.

---------------------------------------------------------------------------------------------
Changes in version 3.2.0:

spr#102
Channel letters on deck cabinet crating labor and materials calculations was improved.
The current algorithm use letters height average to calculate labor and materials quantities for multiple
lines of copy.

spr#142
Error related with the first line wording at the "Channel Letter Backs, Line #"screen was fixed.

spr#143
Proposal writing was improved. Now title of proposal depends on proposal type.

spr#247
Proposals for Lease/Rental agreements was improved. Monthly rate calculation logic was changed and 
now total amount of contract is monthly rate multipled by the number of months.

spr#277
On the "Order Entry" and "Production Schedule" journals, the Job description is not truncated.
Now job description takes 2-3 lines at the "Production Schedule Journal" report.

spr#01319
Now wording "Assembly Labor Post & Panel Signs" is used instead of wording "Assembly Labor".
The materials calculation for the back was improved.

Also was updated inventories costs and labor factors, manual and estimate help. Sample estimates
has been updated and one new sample estimate "UNION7A.est" has been added for this version.
---------------------------------------------------------------------------------------------
Changes in version 3.1.9:

spr#102
Now crating of Channel letters on deck cabinet labor calculations was improved.

spr#111
Now "Housings" material calculation was improved for "Reverse Channel" letters.

spr#102
Now crating of Channel letters on deck cabinet labor calculations was improved.

spr#142
The first line wording at the "Channel Letter Backs, Line #"screen was changed.

spr#143
Now title of proposal depends on proposal type.

spr#277
On the "Order Entry" and "Production Schedule" journals, the Job description is not truncated.

spr#278
Now estimate is compiled when "Store Estimate with no Printout" is chosen.

spr#301
Now when "Select a Customer from List" is chosen at the General Information screen:
if single letter is entered in customer field then list is scrolled to first customer begining 
with this letter;
if several character are entered then list is scrolled to first customer begining with this
characters;

spr#307
The "No" button is now selected by default when user are given the opportunity to delete the
estimate file.

spr#01318
The problem with Pipe rings was fixed.

Implementing SPR# S/F Post & Panel Back Materials.

Fixing SPR#1002ERM ( with Mark Up).
---------------------------------------------------------------------------------------------
Changes in version 3.1.8

Now this version is full compatible with Acct. Link version: estimate files created with Acct. Link version it is 
possible to open with this version now.

---------------------------------------------------------------------------------------------
Changes in version 3.1.7

spr#105
now full support for multiple addresses for the same company added.

spr#217BDB
 Now "Requested Date of Completion" appears on the Job Shop Copy.

spr#242ERM
 Now employee with number of hours worked equal to zero is omitted from the report.

spr#118BDB
 item#1: Now "Closed Job" screen remains after system finish printing "Completed Job Report" and user can close another job(s).
 item#2: Now selected option at the "Select Desired Printout" for "Closed Job" screen is saved and preselected next time the user returns to this screen.
 item#3: "Completed Job Report" "Summary Page" was changed. Now Cell A7 wording is "Type of Sale" and cell B7 contains sale type.

---------------------------------------------------------------------------------------------
Changes in version 3.1.6

SPR151ERM
We have chosen the first solution as you recommended. So now user can
leave "Ornamentation 2, Border/Logo Materials" screen without selection
if user has selected channel border/logo selection at the "Ornamentation
1" screen.
Otherwise user must to select anything before leaving this screen.


SPR#183ERM
now regular pay rate is selected automatically, when other employee is selected.

SPR#184ERM
now default department option is Patterns\CAD

SPR#181ERM
now summary page is printed as required.
Note the item #3 - in version 3.1.5. the value of D36 cell was the AVERAGE of journeyman
costs.

SPR#180ERM
now Work In Progress report is printed from within Track Job even if job is marked
as completed.
now title on report is visible even on non printed report.

SPR#12XERM
now average centroid height tab displays total combined area of all sign cabinets.

Also, engineering module generates a warning message when allowable square pipe sizes
exceed 14 in.

SPR#130ERM
a warning message added to Open job for costing screen, when user writes a work order
but does not open any job on it.

SPR154ERM
 now last used employee remains selected, when different section or different department
are selected.

SPR155ERM
 now users can enter job file names manually.

SPR156ERM
 now Labor Data Entry screen displays accumulated hours for selected pay rate (regular,
overtime, etc.).

SPR158ERM
 now on Work In Progress and Work Completed reports employee work hours are grouped
into single record. Instead of Pay rate a total labor cost for that employee is 
displayed.

SPR#157ERM
 now a page break added before the summary information in Detailed Estimate.

 now on printed journal report column headings are printed on each page.

SPR#153ERM
now costing clerk can specify a completion date on his own- before updating Production
Schedule journals he is given this capability.

SPR#122ERM
now both Production and Order Journals are no longer stored in xls files, their data is
moved to .abc files, where each month/year has a separate .abc file. Journals are available
for editing via Accutrack interface, and can be viewed in MS Excel.

Next, a convenient way for moving orders to another month was implemented.

Modified Order Journal and Production Journal output formats to be more consistent.

Backlog macros can be edited in Excel template directly. Be carefull to edit the template
itself, not its copy!

Also, due to changed handling of Journals data, a data lock conflict probability is 
significantly reduced.

---------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------
Changes in the 2.5.1 version:

Regarding SPR2K010BDB:
Item 1) modified screen "ILLUMINATION 2, FLUORESCENT 1" exit rule,
	removed autoselect on menu screen "ILLUMINATION 1, TYPE".
Item 2) additionall description required.
Item 3) modiefied screen item label.

Regarding SPR2K011BDB:
Item 1) replayed previous SPR item 3.
Item 2) fixed.
Item 3) fixed.

Regarding SPR2K012BDB:
Item 1) and 3) Improved menu path for Zero Crearance Hinge Frames.
Item 2) Fixed consatant generation.

Regarding SPR2K013BDB:
Item 1) added new custom material which sumarize previous materials list.
Item 2) fixed.

---------------------------------------------------------------------------------------------
Changes in the 2.5.2 version:

Regarding SRP2K014BDB:
Item 1) fixed
Item 2) added additionall menu skipig rules.
Item 3) tested. Try again, on us site workig.
Item 4) added desired labor factors to prevent 'Illegal selection' message.
Item 5) the costs of the balasts was not provided. 
	The costs for the balasts dublicated from corresponding older balasts.
	Then user creates new estimte the estimate stores the system configuration to it self.
	Then estimate is opened user can change system setting just for currently opened estimate.
	If no estimate are opened, user can change global system settings, which will applyed for the new estimates.
	Balasts filtering by the brand are fixed.
Item 6) desciption are improved.
Item 7) we can't get this effect. We tryed on most different computers with different OS. Try upgrade your system.

Regarding SRP2K015BDB:
Item 1) same as SPR14 item 7.
Item 2a) fixed.
Item 2b) description improved.
Item 2c) fixed.
Item 2d) fixed.
Item 2e) description improved, partial changes was maded by the SPR11 item 3.
Item 3) improved application functionality to gat a posibility dynamicaly change currently runing screen items value.

Regarding SRP2K016BDB:
Item 1) decreased Estimate report size.
Item 2) just Excel is needed for ABC Estimate software.
Item 3a) other report you can found on the separated worksheets. Look to sheet tab.
Item 3b) font size is noe 10pt.
Item 3c) from 'Job Shop Copy' report removed unneeded information to save the pages.

---------------------------------------------------------------------------------------------
Changes in the 2.5.3 version:

1) Included nondemo libraries for KeyLockII.
2) Prevent to store empty clients information to file.

---------------------------------------------------------------------------------------------
Changes in the 2.5.4 version:

Added save as command.

Regarding SPR2K035GLB: date 03/22/2000
Template JobShopCopy.xlt updated regardint this SPR.

Regarding SPR2K034GLB: date 03/22/2000
Problem fixed.

Regarding SPR2K017BDB: date 03/21/2000
Problem fixed.

Regarding SPR2K036GLB: date 03/22/2000
Problem fixed.

Regarding SPR2K052RWB: date 03/22/2000
Created new menu "CREATE SHELL MATERIALS SCREEN". This screen will appear in the menu queue if user selected
"Create & Ship" item on the screen "General information 2". However this menu will not apear if use selects 
"Fabricated letters" on the "General information 3" screen, except for "Routed backgroud" letter type.

Regarding SPR2K052RWB: date 03/21/2000
Nothig changed as you wich on the e-mail subject "2 different SPRs both identified as SPR 052" dated Wednesday, March 22, 2000 6:59 PM

Regarding SPR2K040BDB: date 03/23/2000
Regardint this problem, are changed materials description and costs.

Regarding SPR2K029RWB: date 03/16/2000
Implemented solution described in the email which is sended to Brian (subject "SPR#" dated 03/24/2000)

Regarding SPR2K028RWB: date 03/14/2000
Menu items caption is corrected.

Regarding SPR2K026RWB: date 03/14/2000
C-Cover Splice Clips is generated for Access or Wide Fabricated frames.
C-Cover Corner Flashing corrected amount to two pre sign.

Regarding SPR2K024RWB: date 03/14/2000
Corrected units.

Regarding SPR2K027RWB: date 03/16/2000
Now gasker tape generating just for Access Frame and Wide Fabricated Frame.

Regarding SPR2K018BDB: date 03/21/2000
Item 1) Changed constant calculation. Now is: if single face is selected constant is 1.5 for double face constant is 2.
Constant independs on size of sign.
Item 2) Corrected sign size checking rule. 
Item 3) No error are detected in the 2.5.3 version.
Item 4) Added paint material quntity generation for Post&Panel estimates, using logic as for "Type IV Frame".
Item 5) Amount of labor and material now corectly are multiplyed by count of identical signs. Amount of labor and
materials for "Patterns/CAD" department are not multiplyed.
Item 6) Descriptions for labors and meterials is corected.
Item 7) Added exit rule which dont allow to user leave the screen if is selected Post&Panel for 3 or 4 faces sign.

Regarding SPR2K050RWB: date 03/21/2000
Number changed to 125%.

Regarding SPR2K021RWB: date 03/16/2000
Problem fixed.

Regarding SPR2K051RWB: date 03/17/2000
Caption changed.

Regarding SPR2K022RWB: date 03/14/2000
Nothing changed regardind your wish which come letter.

Regarding SPR2K023RWB: date 03/16/2000
Fixed.

Regarding SPR2K02RWB: date 03/14/2000 and SPR2K025RWB: date 03/16/2000
"Primer" are removed.

---------------------------------------------------------------------------------------------
Changes in the 2.5.5 version:

Regarding e-mail by 
From: Brooks, Brian <BrianB@abcsignproducts.com>
Subject: RE: SPR29
Changes regardint "Paint Outside Surface Of Metal Back" selection:
1) If user has selected "Extrusion" at the "General Information 3" screen:
	a) If user has selected "24 Gauge Sheet Metal" as the type of back material, system will work like DOS
	version. "Paint Outside Surface..." selection doesn't effects paint quantity calculation.
	b) For all other types of material for back; if the user has selected "Paint Outside Surface.."	
	then will be calculated paint quantity needed to paint one side of the metal.
2) If user has selected "Sheet Metal" at the "General Inforamtion 3" screen, the system works like
DOS version (the amount is doubled). "Paint Outside Surface" doesn't effects paint quantity calculation.

Changes regarding for selecting the various materials for the create "shell":
Screen "Create shell materials". This screen appears then user selects "Create & Ship" at the
"General Information 2" screen. And screen apprears for all signs types or for "Routed", "Channel", "Channel with routed faces" letters	
if only "Fabricated Letters" at the screen "General Information 3" have been selected without selecting 
it in combination with any other available selection at this screen.

---------------------------------------------------------------------------------------------
Changes in the 2.5.6 version:


Regarding SPR 2K037GLB: 
Fixed. Misspels corrected.


Regarding SPR 2K042BDB: 
This is so much difficult to achieve. (The current system logic not alow to do that).


Regarding SPR 2K024rwb: (revised)
Expresion to calculate "Waxed Paper" for Routed Letters was modified, bug fixed.


Regarding SPR 2K054RWB: date 04/07/2000
This problem has been corrected in the 2.5.5 version.


Regarding SPR 2K039GLB: 
Items A) B) C) fixed
Item D) note that your sample contains negative sales discount. Formula in cell [D] says,
that cell [C] should be multiplied by (1-sales_discount_percentage). If sales dicoumt percentage
is negative, the result in cell [D] shall be greater that value in cell [C].


Regarding SPR 2K038GLB: 
Done as requested.


Regarding SPR 2K041BDB: 
Item 1) all reports are designed for letter pages size.
Item 4) manufacture order template undated, other reviewed.
Item 5) One blank line added between departments. Page break added.
...

Regarding SPR 2K057RWB: 
Item 1) - 2) Expressions have been modified as required in the SPR.

Regarding SPR 2K055RWB: 
Item a) - b) Related expression have been corrected. Now material "Cooley Magic" quantity
is generated ok. (unit of measurement is gallons)


Regarding SPR 2K043DB: 
Item 1) "Sharing Violation" means that specified file is opened by current or other user and software
can't read estimate file information needed. Estimate file can be opened just by one process
at the moment. But to print Open Estimate Report system must read information about all
estimates which are in the '<abc_directory>\Estimates' directory. User which creating this report
must know that not all estimates can by opened at this moment.
Item 2) Now for "Post & Panel" type of signs is automatically calculated quantity of materials at the
"Background Color Selection" menu. New action codes 310 and 311 have been craeted.


Regarding SPR 2K080RWB: 
On the example estimate file 'TEST NON-WELD.EST' was mistakelly selected not Small E-Z but Type IV frame.
For Small E-Z frames 'Type II BAck Adapter' is not generated.


Regarding SPR 2K081RWB: 
Problem fixed. Now program will automatically selects 1 switch just for new estimates.
And if user reenters switch count (exapmle to 0), automatical selection will switches off.


Regarding SPR 2K061GLB: 
Problem is not recrated - our testing shows that in Estimated & Actual materials data columns
is cost, not selling price is printed. Also regarding incorrect Estimated & Actual labor calculating - used
algorithms are identical as in DOS version - estiamted labor cost is the result of multipaying total estimate 
hours and journeyman cost for the department, actual labor cost is the SUM of multiplications 
EmployeePayRate * EmployeeWorkHours.


Regarding SPR 2K062: 
Company name is centered on the Job and Shop Order reports.


Regarding SPR 2K063GLB: 
Template 'workcompleted.xlt' and script wr_in_progress updated.


Regarding SPR 2K064GLB: 
Explanation e-mail proposed: Subj:SPR #2K064GLB dated:4/10/2000 To: Brian Brooks From: Tomas Baltramaitis


Regarding SPR 2K065GLB: 
Script 'handle_journals.vbs' updated to perform the work descriptions. Code added for removing
word "manufacture".


Regarding SPR 2K045DB: 
Item 1) improved menu file syntax to be able to set enable/disable 
flag for imput negative number.
Item 2) Exit rule at the menu "Background Color Selection" has been changed. if user has selected
"Apply Background Color..." selection then he must select some material type from the list on
this screen.
Item 3) requested text is changed to "Select a Network Directory where server application is installed".
Be cause then user installs application as network type, installation program will
install just executables and sets link to a selected network directory. 
Item 4) At the "General Inform. 3" menu, exit rule works ok. User must to make selectionat this menu
before leaving it.
Item 5) At "Manual or CAD/CAM, Line #" menu "CAD/CAM" and "Machine 1" menu items are preselected. If user
need he can deselect these options.
Item 6)Job description has been changed. "Sign Face Material" will not be included if no selection have been
made at the "Plastic 1" menu.
Item 7) Now exit rule will require the user select "Size" and enter dimensions at the
"Plastic Face Only" menu.
Item 8) At the "Sheet Metal 1" menu "Size" now will be preselected. Now is not option to place cursor
in the first input field.


Regarding SPR SPR2K018BDB : Revisited : date Wednesday, April 05, 2000 5:09 PM
Related expresion in the 'bill_mat_nm.src' has been modified.


Regarding SPR 2K067GLB : 
Misspells checked.


Regarding SPR 2K066GLB: 
Now user can choose from Statistics menu to open journal type (Order or Production).
User must select from list of files required journal and it be opened in Excel.
Note that jounal name is constructed as follows: 
journaltype("shedule" or "order"), month digit, and year digit
Example: 'order4_2000.xls'


Regarding SPR 2K058RWB: 
Item 1) - 2) These problems has been fixed. We check is variable FACES_ROUTED in all expressions with 
prefix "R"(variable value depends on iteration).


Regarding SPR 2K068GLB: 
Macros text updated. Spelling error reviewed.
Removed "Sales Agreement And Conditions" text from Short Form Proposal.
If you found any mispells on the "Sales Agreement And Conditions" text, please refer exactly 
words in the text to be corrected. 


Regarding SPR 2K053RWB:
There have been implemented new expressions to calculate "1x4" lumber and "Cardboard sheet" materials
quantities for "Plastic face Only" and "Routed Background Panels". materials "2x4" lumber and 
"Foam Padding" now will not be generated.


Regarding SPR 2K046DB:
Export/import labor factors and inventories feature is needed in case of updating
'labor_nm.abc' or 'invent_nm.abc' files. In future, if user would be like to update 
labor database file and hi/shi needs keep the current labor factor, user can export 
it to backup file, after labor database file are updated user can restore the previous 
labor factors. Similar is for inventory database if user will save current costs of 
inventories.
The backup files are just binary data files, and user can't view it using Excel or Word.


Regarding SPR 2K082RWB:
Labor factors descriptions have been changed as required. Also have been changed letters height
checking rules as required


Regarding SPR 2K083RWB:
This bug has been fixed. There was variable CRATE_SHIP_SIGN with prefix "R" in the labor676. It
was wrong.


Regarding SPR 2K084RWB:
There has been modified expression to calculate labor factor in the "PATTERN/CAD" department.
Identical bug has been found in the "CAD/CAM Machine Time" department and has been fixed. Now
if user inputs a substitute amount this amount will be used in the calculations.

---------------------------------------------------------------------------------------------
Changes in the 2.5.7 version:

SPR#18
We have understood this problem and fixed it. Now into cell in the column with heading "Amount"
is entered number of "Multiple Identical Sgns". If user doesn't enter anything here, value will
be "1". The amount shown in the "Unit Cost" column is equal to the "Cost of Buy-out Knock-Down Kit"
provided at the "Extrusion 1, Frame Type" menu, and the amount in the "Cost" Column is equal
to the "Amount" multiplied by the "Unit Cost".

SPR 2K047DB:
Ploblem fixed, UI updated.

SPR 2K085RWB:
This problem has been corrected. Some variables had been declarated with
prefix "R" (they value depends on iteration). It had been wrong because these variables values
don't depends on iteration.
Also this problem has been detected in the others expressions at this
department and we have fixed it.

SPR 2K086RWB:
This bug has been fixed (related bill_mat expression has been modified).

SPR 2K090GLB:
Template file ant report building code updated to treat sales discount percentage 
correctly.

SPR 2K091GLB:
Font increased, misspell corrected.

SPR 2K049BDB:
Options default text updated.

SPR 2K070BDB:
1) Filter name "BRAND" changed to "BRAND_OF_BALLAST"
2) Added message dialog window and automatically call the Jornyman Cost and Rate 
update dialog window, at the time when application first time runs.

---------------------------------------------------------------------------------------------
Changes in the 2.5.8 version:

Improved ABC Software security, to prevent date roll back.

---------------------------------------------------------------------------------------------
Changes in version 3.1.0:

#1
Post & Panel Signs.
If no "Method of Mounting" is chosen at the "General Information 2" menu
then no labor and material
will be generated in the "Installation" department.

If one of first three "Method of Mounting" is chosen (Wall Mounted,
Column Mounted or Structure
Mounted) then labor and material will be generated in the "Installation"
department. "Wall Mounted",
"Column Mounted" or "Structure Mounted" method selection only indicates
that "Post & Panel" sign will be
installed and needed constant, labor and material will be generated in
the "Installation" department.

If "Crate & Ship" or "Load for shipping, Uncrated" is chosen then needed
labor and material will be
generated (as in the previous versions).

#2 Help files of estimate and engineering updated/fixed.

#3 Open Jobs report now may be printed in 5 different forms.

#4 Overtime/holiday/regular multipliers are added- Work Order Configuration
  and Enter Labor Data screens are updated, Open Jobs Report and Work in 
  Progress/Completed reports now use employees pay rate that was valid during
  making work hours entry.

#5 Demo estimates that come with installation, are updated.

---------------------------------------------------------------------------------------------
Changes in version 3.1.1:

- added automatic customer information transfer to proposal writing screen

- fixed problems regarding text-off on right margin of Proposal on preprinted
  pages.

- fixed problems regarding text-off on bottom margin of Job Order (Shop Copy).

- changed security algorithm. Now it is not allowed to start the application if
  computer date indicates the date before 05/22/2000. Also the last start date
  is recorded for catching the gambling with computer date.

- help for User manager and registration code generator updated.

---------------------------------------------------------------------------------------------
Changes in version 3.1.2.:

Added automatic serial number gathering if the dongle key is attached to the computer or is
accessible on the network.
Manual (Installation part) is updated.


by SPR#73:
- right margin increased to 1/2 inch - this should be enough for most printers.

by SPR#74:
- Now description generated by estimating module list all pipes (tubes) when user
   "Repeat(s) for Staged Pipe".
   
-  We have added instruction above this menu item that users turn attention to entered size.
   We have created new exit rule for this menu screen. User can leave this menu screen if:
                - nothing are selected;
                - if entered size <= 24 for Used or New Pipe or <=14 for Square Tube and/or entered 
		  length
                  for pipe or sq. tube;
                - if entered size > 24 for Used or New Pipe or > 14 for Square Tube and/or entered 
		  length
                  and selected "Non-Inventory Item" and entered Cost and Markup.
                  
   Also we have chanded unit of measurement from "each" to "ft" for "Non-inventory column" 
     material.

by SPR#75:
- now "New Work Order - General Information screen" searches the customers database and retrieves
   his data automatically. Search is activated upon hitting Enter key in customer name field (or any
   other action that causes the cursor to move off the customer name field), if no customer found 
   under given name- no data is retrieved, no error messages displayed.

- Now shipping and billing information is stored separately and displayed as required. If empty work
   order is being created, and upon customer search in database his data is found, the user is asked
   whether he wishes to add customer data to shipping information screen too.

- removed NO CHARGE label from Job Orders. Now this label appears only in Shop Orders.

---------------------------------------------------------------------------------------------
Changes in 3.1.3 version

Regarding SPR100:

"7.50" x 9" x 1/4" Steel Plates" material quantity calculation
expression has been modified.
Also we had saw analogical problem as if "Small A Bleed Frame" had been
selected in combination
with "Pipe Holes & Hardware" ("6.00" X 8" X 1/4" Steel Plates"
material). So we have corrected it.


---------------------------------------------------------------------------------------------
Changes in 3.1.4 version

Regarding SPR76:

Impoved security of Engineering module.
Added information message in case top of Licensed users is reached.
Improved software server installation. Remember: NetBEUI protocol must be installed on all computers
to normally work the KeyLockII network service.

---------------------------------------------------------------------------------------------
Changes in 3.1.5 version

Regarding additional fixes to SPRs #72 & #73
Now Proposal should be printing on Cannon printers OK. Problems with
right margin of Open Job Report not detected even with Cannon printers,
so only option for centering report on page horizontally added. IN case
problem reappears, please detail it.

Regarding SPR 2K074BDB

Message about columns sizes have been changed at the menu "Installation
7, Column Size".
Also the description which is generated by the estimate module have been
modified as required in this
SPR item 2.

Regarding SPR 2K078BDB
Now filter added to trim Tax amount to 2 decimal places. Link to sample
Estimates added to Help menu of ABC Estimate application. Glossary created
and included with ABC Estimate help, link to glossary added to Help menu
of ABC Estimate application. Incorrect text in cell 2U fixed.

Regarding SPR 2K079BDB

We have fixed this problem. Now menu "Background Color Selection"
appears only once, unless
user selects "Repeat this Menu" menu item.

Regarding  SPR 2K100RWB

We have tested this problem. Everythink works ok. Needed material "
7.50" x 9" x 1/4" Steel
Plates" is generated.

Regarding  SPR 2K101RWB

As we have understood "C-Cover Clips" means "C-Cover Splice Clips".
"C-Cover Splice Clips"
are generated if user have selected "Splice Frame" and entered "Number
of Splices" at the
"Extrusion 5, Fabrication Extras". So we have not modified expressions
related with this material because
quantity calculation for it depends on selection described above.
We have modified expressions related with "Gasket Tape" and "Wire Clips"
materials in the
bill_mat_nm.src file. These materials will not be generated for Type II
Wide Fab selection.(As required)

Regarding SPR 2K110BDB

Problems with not transferred information arises from incorrect version
of scripts_nm.abc file. Please always make sure this file was exactly the
same as was included with installation files.
Column Invoice Date added to Order Entry Journal Mo and JO pages.

