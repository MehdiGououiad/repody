import { readFileSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { LOCAL_HOST_LIST, LOCAL_HOSTS_LINE } from "./k8s-local-common.mjs";

function hostsFilePath() {
  return process.platform === "win32"
    ? "C:\\Windows\\System32\\drivers\\etc\\hosts"
    : "/etc/hosts";
}

function missingLocalHosts() {
  let hostsText = "";
  try {
    hostsText = readFileSync(hostsFilePath(), "utf8");
  } catch {
    return [...LOCAL_HOST_LIST];
  }
  return LOCAL_HOST_LIST.filter((host) => !hostsText.includes(host));
}

/** @param {{ root: string, run: (cmd: string, args: string[]) => void }} options */
export function createHostsCommands({ root, run }) {
  function ensureHostsHint() {
    const missing = missingLocalHosts();
    if (missing.length === 0) return true;
    const hostsPath = hostsFilePath();
    console.error("\n✗ Hosts file missing Repody entries — browser sign-in will fail (OAuth uses *.repody.local)");
    console.error("  Run: pnpm k8s:local:hosts");
    console.error(`  Or add to ${hostsPath} (admin):`);
    console.error(`  ${LOCAL_HOSTS_LINE}`);
    console.error("");
    return false;
  }

  function cmdHosts() {
    const hostsPath = hostsFilePath();
    const missing = missingLocalHosts();
    if (missing.length === 0) {
      console.error(`Hosts file already has Repody entries (${hostsPath})`);
      return;
    }
    console.error(`Missing: ${missing.join(", ")}`);
    console.error(`\nAdd this line to ${hostsPath}:\n\n  ${LOCAL_HOSTS_LINE}\n`);
    if (process.platform === "win32") {
      const scriptPath = path.join(
        process.env.TEMP || root,
        `repody-hosts-${Date.now()}.ps1`,
      );
      const ps = [
        `$line = '${LOCAL_HOSTS_LINE}'`,
        `$path = '${hostsPath.replace(/\\/g, "\\\\")}'`,
        `$pattern = 'app\\.repody\\.local|api\\.repody\\.local|files\\.repody\\.local|auth\\.repody\\.local|argocd\\.repody\\.local|grafana\\.repody\\.local|bugsink\\.repody\\.local|harbor\\.repody\\.local'`,
        `$content = @(Get-Content -LiteralPath $path -ErrorAction SilentlyContinue | Where-Object { $_ -notmatch $pattern })`,
        `($content + $line) | Set-Content -LiteralPath $path -Encoding ASCII -Force`,
        `ipconfig /flushdns | Out-Null`,
        `Write-Host 'Done. Repody hosts entries updated.'`,
      ].join("\n");
      writeFileSync(scriptPath, ps, "utf8");
      console.error("Opening elevated PowerShell to update hosts (approve UAC)...\n");
      run("powershell", [
        "-NoProfile",
        "-Command",
        `Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','${scriptPath.replace(/'/g, "''")}'`,
      ]);
      try {
        unlinkSync(scriptPath);
      } catch {
        // Best effort cleanup.
      }
      return;
    }
    console.error(
      `On Linux/macOS, remove stale repody.local lines and add:\n  echo '${LOCAL_HOSTS_LINE}' | sudo tee -a ${hostsPath}`,
    );
  }

  return { cmdHosts, ensureHostsHint };
}
