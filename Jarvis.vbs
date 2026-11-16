Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c ollama serve", 0, False
sh.Run """" & sh.CurrentDirectory & "\.venv\Scripts\pythonw.exe"" main.py", 0, False
