const { spawnSync } = require("child_process");
const path = require("path");

const INTERVAL_MS = 5000;
const PROJECT_ROOT = path.resolve(__dirname, "..");

function git(args) {
    return spawnSync("git", args, {
        cwd: PROJECT_ROOT,
        encoding: "utf8",
        stdio: "pipe",
    });
}

function run() {
    // Get all changed/untracked files
    const status = git(["status", "--porcelain"]);
    if (!status.stdout.trim()) {
        console.log("⏭  Nothing new, skipping...");
        return;
    }

    const files = status.stdout
        .trim()
        .split("\n")
        .map(line => line.trim().replace(/^[MADRCU?\s]+/, "").trim())
        .filter(Boolean);

    let committed = 0;

    for (const file of files) {
        // Stage just this one file
        git(["add", file]);

        const diff = git(["diff", "--cached", "--name-only"]);
        if (!diff.stdout.trim()) continue;

        const message = `auto: update ${file} — ${new Date().toLocaleTimeString()}`;
        const commit = git(["commit", "-m", message]);

        if (commit.status === 0) {
            console.log(`✅ Committed: "${message}"`);
            committed++;
        }
    }

    if (committed === 0) {
        console.log("⏭  Nothing committed");
        return;
    }

    // Push all commits at once after individual commits
    const push = git(["push", "origin", "main"]);
    if (push.status === 0) {
        console.log(`🚀 Pushed ${committed} commit(s)\n`);
    } else {
        console.log("❌ Push failed:", push.stderr.trim());
    }
}

console.log("⚡ Watching:", PROJECT_ROOT);
console.log("🔁 Checking every", INTERVAL_MS / 1000, "seconds\n");

run();
setInterval(run, INTERVAL_MS);