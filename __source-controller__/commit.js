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
    git(["add", "."]);

    const diff = git(["diff", "--cached", "--name-only"]);
    if (!diff.stdout.trim()) {
        console.log("⏭  Nothing new, skipping...");
        return;
    }

    const message = `auto: ${new Date().toLocaleTimeString()}`;
    git(["commit", "-m", message]);

    const push = git(["push", "origin", "main"]);
    if (push.status === 0) {
        console.log(`🚀 Pushed — "${message}"`);
    } else {
        console.log("❌ Push failed:", push.stderr.trim());
    }
}

console.log("⚡ Watching:", PROJECT_ROOT);
console.log("🔁 Pushing every", INTERVAL_MS / 1000, "seconds\n");

run(); // run once immediately
setInterval(run, INTERVAL_MS);