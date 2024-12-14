# Unreal Exporter Addon

## **Description**
The **Unreal Exporter** addon simplifies exporting 3D meshes for Unreal Engine by allowing you to export selected objects or their hierarchies individually. Each exported object is positioned at the world origin, maintaining its original pivot point. This ensures accurate origins for drag-and-drop import into Unreal Engine and consistent reimport behavior.

This tool is perfect for artists looking to streamline their asset export workflow for Unreal Engine, with options for organizing paths, exporting selected objects, or entire hierarchies, all with precision and simplicity.
This addon was designed in the use of any import in engine, no matter the engine (work with unity, godot, ...). This addon is released under the [GNU General Public License v3](https://github.com/Tarmunds/Blender_Unreal_Export_Addon/blob/main/LICENSE).

![BlenderPanel](https://github.com/Tarmunds/Blender_Unreal_Export_Addon/blob/main/Images/Panel_Blender.png)

---

## **Features**
1. **Export Selected Objects:**
   - Export individual meshes with their original pivot points to the world origin.
   - Ideal for clean imports into Unreal Engine without needing additional adjustments.
  
![SelectedObjects](https://github.com/Tarmunds/Blender_Unreal_Export_Addon/blob/main/Images/Selected_Object.gif)

2. **Export Object Hierarchies:**
   - Export entire parent-child hierarchies as single objects, simplifying complex asset exports.
  
![SelectedHierarchy](https://github.com/Tarmunds/Blender_Unreal_Export_Addon/blob/main/Images/Selected_Hierarchy.gif)

3. **Path Management:**
   - Easily set and save export paths using the addon’s UI.
   - Supports dynamic path selection and dropdown options for saved paths.
  
![PathManagement](https://github.com/Tarmunds/Blender_Unreal_Export_Addon/blob/main/Images/Saved_Path.gif)

4. **Include/Exclude Transformations:**
   - Optional toggle to keep the object transformation in the world (not reset at the origini).

5. **Customizable Shortcuts:**
   - Add custom shortcuts to streamline your workflow by right-clicking on any button and assigning a shortcut.

---

## **How to Use**
### **Set an Export Path**
1. Open the 3D Viewport and press `N` to open the side panel.
2. Navigate to the `Tarmunds Addons` tab.
3. In the **Export Unreal** panel, set an export path:
   - Use an existing folder (you must create the folder beforehand; the addon does not create folders automatically).
   - Enter the path in the `Path` field.

### **Export Options**
1. **Export Selected Objects:**
   - Select the objects you want to export in the viewport.
   - Click the **Export Selected Objects** button to export them individually.
   
2. **Export Hierarchies:**
   - Select a parent object in the viewport.
   - Click the **Export Each Hierarchy** button to export the parent and all its child objects as a single object.

### **Optional Settings**
- **Include Location:**
  - Enable this toggle to include world transformations in the export.
  - Disable it to reset object locations to the world origin.

---

## **Tips**
- To speed up your workflow, assign a custom shortcut to the export buttons by right-clicking and selecting **Assign Shortcut**.
- Use the `Path Options` dropdown to manage and reuse previously saved export paths.

---

## **License**
- This addon is licensed under the GNU General Public License v3, meaning it is free to use, modify, and distribute. Concept of the dagger by Baldi Konjin, you can find it here

---

## **Credits**
- **Kostia Perry (Tarmunds):**
  - Add-on creator, path manager, and UI enhancements.
- **Sacha Veyrier:**
  - Provided the original script concept, later rewritten and improved from scratch by Kostia Perry.

---

## **Contributing and Feedback**
- We are always open to suggestions for new tools or modifications. Feel free to join our community on [Discord](https://discord.gg/h39W5s5ZbQ) to share your ideas and feedback.

— Tarmunds

