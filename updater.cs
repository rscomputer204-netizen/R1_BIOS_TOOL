using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Windows.Forms;

namespace R1Update
{
    class Program
    {
        static void Log(string msg)
        {
            try
            {
                File.AppendAllText("updater.log", string.Format("[{0:yyyy-MM-dd HH:mm:ss}] {1}\r\n", DateTime.Now, msg));
            }
            catch { }
        }

        static void Main(string[] args)
        {
            try
            {
                int pid = 0;
                if (args.Length > 0)
                {
                    int.TryParse(args[0], out pid);
                }

                // 1. Wait for calling process to exit
                if (pid > 0)
                {
                    try
                    {
                        Process proc = Process.GetProcessById(pid);
                        if (!proc.HasExited)
                        {
                            proc.WaitForExit(15000);
                        }
                    }
                    catch { }
                }
                Thread.Sleep(1000);

                // 2. Resolve target application root directory
                string currentDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
                string rootDir = currentDir;

                if (args.Length > 1 && Directory.Exists(args[1]))
                {
                    rootDir = Path.GetFullPath(args[1]);
                }
                else
                {
                    if (File.Exists(Path.Combine(currentDir, "R1_BIOS_TOOL.exe")) || File.Exists(Path.Combine(currentDir, "main.py")))
                    {
                        rootDir = currentDir;
                    }
                    else
                    {
                        DirectoryInfo parentInfo = Directory.GetParent(currentDir);
                        string parent = parentInfo != null ? parentInfo.FullName : null;
                        if (parent != null && (File.Exists(Path.Combine(parent, "R1_BIOS_TOOL.exe")) || File.Exists(Path.Combine(parent, "main.py"))))
                        {
                            rootDir = parent;
                        }
                    }
                }

                Directory.SetCurrentDirectory(rootDir);
                Log(string.Format("Updater started. Root directory: {0}", rootDir));

                // 3. Locate update cache directory
                string[] cacheCandidates = new string[]
                {
                    Path.Combine(rootDir, "update_cache"),
                    Path.Combine(rootDir, "_internal", "update_cache"),
                    Path.Combine(currentDir, "update_cache")
                };

                string cacheDir = null;
                foreach (string cand in cacheCandidates)
                {
                    if (Directory.Exists(cand))
                    {
                        cacheDir = cand;
                        break;
                    }
                }

                if (cacheDir == null)
                {
                    Log("Update cache directory not found.");
                    Relaunch(rootDir);
                    return;
                }

                string payloadDir = Path.Combine(cacheDir, "payload");
                if (!Directory.Exists(payloadDir))
                {
                    Log(string.Format("Payload directory not found: {0}", payloadDir));
                    Relaunch(rootDir);
                    return;
                }

                // 4. Copy all payload files to root directory
                Log(string.Format("Copying payload from {0} to {1}...", payloadDir, rootDir));
                CopyDirectoryRecursive(payloadDir, rootDir);

                // Copy version.txt if present in cache root
                string cacheVer = Path.Combine(cacheDir, "version.txt");
                if (File.Exists(cacheVer))
                {
                    try { File.Copy(cacheVer, Path.Combine(rootDir, "version.txt"), true); } catch { }
                    string internalVer = Path.Combine(rootDir, "_internal", "version.txt");
                    if (Directory.Exists(Path.GetDirectoryName(internalVer)))
                    {
                        try { File.Copy(cacheVer, internalVer, true); } catch { }
                    }
                }

                // 5. Clean up update_cache
                try
                {
                    Directory.Delete(cacheDir, true);
                    Log("Cleaned up update cache.");
                }
                catch (Exception ex)
                {
                    Log(string.Format("Warning: could not delete cache: {0}", ex.Message));
                }

                Log("Update completed successfully! Relaunching application...");
                Relaunch(rootDir);
            }
            catch (Exception ex)
            {
                Log(string.Format("CRITICAL ERROR: {0}", ex));
                MessageBox.Show(string.Format("Update Error:\n\n{0}", ex.Message), "R1 BIOS Tool - Update Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        static void CopyDirectoryRecursive(string sourceDir, string targetDir)
        {
            Directory.CreateDirectory(targetDir);

            foreach (string file in Directory.GetFiles(sourceDir))
            {
                string targetFilePath = Path.Combine(targetDir, Path.GetFileName(file));
                try
                {
                    // Retry copy if file is briefly locked
                    int retries = 5;
                    while (retries-- > 0)
                    {
                        try
                        {
                            if (File.Exists(targetFilePath))
                            {
                                File.SetAttributes(targetFilePath, FileAttributes.Normal);
                            }
                            File.Copy(file, targetFilePath, true);
                            break;
                        }
                        catch (IOException)
                        {
                            if (retries == 0) throw;
                            Thread.Sleep(400);
                        }
                    }
                }
                catch (Exception ex)
                {
                    Log(string.Format("Failed to copy {0} -> {1}: {2}", file, targetFilePath, ex.Message));
                }
            }

            foreach (string subDir in Directory.GetDirectories(sourceDir))
            {
                string dirName = Path.GetFileName(subDir);
                if (dirName.Equals("__pycache__", StringComparison.OrdinalIgnoreCase)) continue;
                string targetSubDir = Path.Combine(targetDir, dirName);
                CopyDirectoryRecursive(subDir, targetSubDir);
            }
        }

        static void Relaunch(string rootDir)
        {
            string[] exeCandidates = new string[] { "R1_BIOS_TOOL.exe", "main.exe", "R1_BIOS_EDITOR.exe" };
            foreach (string exeName in exeCandidates)
            {
                string exePath = Path.Combine(rootDir, exeName);
                if (File.Exists(exePath))
                {
                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = exePath,
                        WorkingDirectory = rootDir,
                        UseShellExecute = true
                    };
                    Process.Start(psi);
                    return;
                }
            }
        }
    }
}
