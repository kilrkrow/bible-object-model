# Build it on a Windows PC

These steps build everything on a Windows PC, natively, with no WSL. The first run takes a few minutes, mostly
to download the sources. After that, rerunning the build takes about a minute.

## 1. Install two things (once)

- **Python 3.10 or newer** from https://www.python.org/downloads/. On the first screen of the installer,
  tick **Add python.exe to PATH**.
- **Git for Windows** from https://git-scm.com/download/win. The installer's defaults are fine.

Open a new PowerShell window after installing, so it can find both.

## 2. Get the code (once)

Pick a folder for it, for example `C:\Code`, then:

```
cd C:\Code
git clone https://github.com/kilrkrow/bible-object-model
cd bible-object-model
```

This gets the branch GitHub shows first. To pick a branch yourself, add `-b` and its name to the clone,
for example `git clone -b main https://github.com/kilrkrow/bible-object-model`.

## 3. Build and test

From the `bible-object-model` folder:

```
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

`-ExecutionPolicy Bypass` lets this one script run without changing any Windows setting.

The script does five things:

1. It checks for Git and Python.
2. It makes a private Python environment in `.venv`, so nothing is installed into your main Python.
3. It installs `requirements.txt`.
4. It fetches every source at its pinned version and builds `dist\`.
5. It runs the tests.

It ends by printing where the files are, plus a ready-made block for Claude Desktop's config.

To skip the tests, add `-SkipTests`.

## 4. What you get

| Path | What it is |
|---|---|
| `dist\acts-core.sqlite` | The data file. |
| `dist\graph\index.html` | The relationship graph. Double-click to open it; it works offline. |
| `dist\maps\paul-journeys.svg` | Paul's route. |
| `dist\vault\` | Obsidian notes. Copy the folder into a vault, or open it as a vault of its own. |

The script also prints a **Data hash**, a fingerprint of everything in the data file. For the commit that added
this page it was `c0f1538e341bdf431266f24a27151c00e94bb2d1fa3e7a7cda3bd3377351cdf2`; later changes to the data
change it. The file's own bytes can differ between PCs, because SQLite writes its version number into the file,
but the data hash does not. The tests are the real check.

## 5. Hook it to Claude Desktop or Claude Code

The script prints a block like this, with your own paths filled in:

```json
{
  "mcpServers": {
    "bible-object-model": {
      "command": "C:\\Code\\bible-object-model\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Code\\bible-object-model\\mcp_server\\server.py"]
    }
  }
}
```

In Claude Desktop, open Settings, Developer, Edit Config, and merge that `bible-object-model` entry into the
`mcpServers` section. Then restart Claude Desktop.

For Claude Code, run this from the repo folder:

```
claude mcp add bible-object-model -- "$PWD\.venv\Scripts\python.exe" "$PWD\mcp_server\server.py"
```

## Getting the latest changes later

```
git pull
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

## If something goes wrong

- **"Git was not found" or "Python was not found":** install it as in step 1, then open a *new* PowerShell window.
- **A source file "does not match sources.lock.json":** the download was cut short or changed. Delete the
  `sources` folder and run the script again.
- **A test fails:** the script stops there and the build in `dist\` is still usable. The test's message says
  which check failed. Send that message to Claude.
