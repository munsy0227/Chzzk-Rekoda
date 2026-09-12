Option Explicit
Dim shell, files, root, command, argument, shortcut
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
' A .vbs file uses the system script icon; provide a project-local shortcut.
' Refresh its paths after the installation folder moves. Read-only folders
' must still be able to launch the GUI.
On Error Resume Next
Set shortcut = shell.CreateShortcut(root & "\Chzzk Rekoda.lnk")
shortcut.TargetPath = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
shortcut.Arguments = "//nologo " & Quote(root & "\chzzk_gui.vbs")
shortcut.WorkingDirectory = root
shortcut.IconLocation = root & "\assets\chzzk-rekoda.ico,0"
shortcut.Description = "CHZZK Rekoda"
shortcut.Save
On Error GoTo 0
command = "uv run --extra gui --gui-script " & Quote(root & "\chzzk_gui.py")
For Each argument In WScript.Arguments
    command = command & " " & Quote(argument)
Next
shell.Run command, 0, False

Function Quote(value)
    Quote = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
