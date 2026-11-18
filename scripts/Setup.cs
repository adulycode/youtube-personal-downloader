using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;

class Setup {
    static int Main(string[] args) {
        Console.OutputEncoding=Encoding.UTF8;
        bool test=args.Length==2 && args[0]=="--test-root";
        string temp=Path.Combine(Path.GetTempPath(),"YouTubeDownloaderSetup-"+Guid.NewGuid().ToString("N"));
        try {
            Console.WriteLine("YouTube Personal Downloader - All-in-one Setup");
            Console.WriteLine("Preparing bundled tools. No Python installation or GitHub login is needed.\n");
            Directory.CreateDirectory(temp);
            string zip=Path.Combine(temp,"payload.zip");
            using(Stream source=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using(FileStream destination=File.Create(zip)) { source.CopyTo(destination); }
            string package=Path.Combine(temp,"package");
            ZipFile.ExtractToDirectory(zip,package);
            string script=Path.Combine(package,"native","install.ps1");
            string command="-NoProfile -ExecutionPolicy Bypass -File \""+script+"\"";
            if(test) command+=" -InstallRoot \""+Path.GetFullPath(args[1])+"\" -SkipRegistration -NoOpen";
            ProcessStartInfo start=new ProcessStartInfo(Path.Combine(Environment.SystemDirectory,"WindowsPowerShell","v1.0","powershell.exe"),command);
            start.UseShellExecute=false;
            // Ignore module paths inherited from other PowerShell editions or launchers.
            start.EnvironmentVariables["PSModulePath"]=Path.Combine(Environment.SystemDirectory,"WindowsPowerShell","v1.0","Modules");
            Process process=Process.Start(start);process.WaitForExit();
            if(process.ExitCode!=0)throw new Exception("Installer stopped. Details are above. Temporary files: "+temp);
            Console.WriteLine("\nInstalled successfully. Chrome still requires Load unpacked once.");
            // Delete only our unique temporary staging directory, never the install target.
            string parent=Path.GetFullPath(Path.GetDirectoryName(temp)).TrimEnd(Path.DirectorySeparatorChar);
            if(parent==Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar) && Path.GetFileName(temp).StartsWith("YouTubeDownloaderSetup-")) {
                try { Directory.Delete(temp,true); } catch { }
            }
            if(!test){Console.WriteLine("Press Enter to close.");Console.ReadLine();}
            return 0;
        } catch(Exception error) {
            Console.WriteLine("\nSetup failed: "+error.Message);
            if(!test){Console.WriteLine("Press Enter to close.");Console.ReadLine();}
            return 1;
        }
    }
}
