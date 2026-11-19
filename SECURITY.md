# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for a security problem. Use GitHub's private
reporting instead: on the repository page choose **Security → Report a vulnerability**
([direct link](https://github.com/Nikolaos-Paximadakis/sru-generator/security/advisories/new)).
Include what you found, how to reproduce it and which version is affected.

You will get an acknowledgement and either a plan for a fix or the reason none is
needed. Only the latest release receives fixes.

## Things worth knowing

- **SRU files are personal data.** They contain a personnummer, a name and your
  financial transactions. The package writes them readable by their owner only
  (`0600` on Linux and macOS); treat them like any other tax document.
- **Never paste a real personnummer, SRU file, trade export or log output into an
  issue.** Reduce the problem to made-up numbers first.
- **Prefer the environment or a profile file for the CLI.** `--personal-number` is
  saved in shell history and visible in the process list; `SRU_PERSONAL_NUMBER` or
  `--profile me.json` are not.
- **Logging is off unless you turn it on.** Importing the package configures no log
  handler. If you enable logging (or `sru-generator -v`), messages can include stock
  names and amounts.
- **No network access, no telemetry.** The package reads and writes only the files
  you name, and has no runtime dependencies outside the Python standard library.
- Releases are built and published by GitHub Actions with PyPI Trusted Publishing; no
  upload token exists to be leaked.
