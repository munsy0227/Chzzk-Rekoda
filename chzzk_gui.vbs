Option Explicit
Dim shell, files, root, command, argument
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
command = "uv run --extra gui --gui-script " & Quote(root & "\chzzk_gui.py")
For Each argument In WScript.Arguments
    command = command & " " & Quote(argument)
Next
shell.Run command, 0, False

Function Quote(value)
    Quote = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
