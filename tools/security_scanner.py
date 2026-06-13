import re


class SecurityScanner:
    # Compile regex patterns for secret scanning
    SECRETS_PATTERNS = {
        "Private Key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "OpenAI API Key": re.compile(r"sk-[a-zA-Z0-9]{32,}|sk-proj-[a-zA-Z0-9_-]{40,}"),
        "Generic Password/Secret Key Assignment": re.compile(r"(password|secret_key|api_key|token|private_key|auth_token)\s*=\s*['\"][a-zA-Z0-9_\-\.\:\/\@\%\!\#\^\&\*\(\)\+]{16,}['\"]", re.IGNORECASE),
        "AWS Access Key ID": re.compile(r"AKIA[0-9A-Z]{16}"),
        "Slack Token": re.compile(r"xox[bapts]-[0-9a-zA-Z]{10,}")
    }

    @classmethod
    def scan_code(cls, code_content: str) -> dict:
        """
        Scans code content for hardcoded secrets, passwords, or api keys.
        Returns check status and list of findings.
        """
        findings = []
        lines = code_content.splitlines()

        for name, pattern in cls.SECRETS_PATTERNS.items():
            for idx, line in enumerate(lines, 1):
                match = pattern.search(line)
                if match:
                    # Obfuscate the found secret in the logs to prevent leaking it in stdout
                    secret = match.group(0)
                    if len(secret) > 10:
                        obfuscated = secret[:4] + "..." + secret[-4:]
                    else:
                        obfuscated = "..."
                    findings.append(
                        f"Line {idx}: Potential {name} leaked: {obfuscated}")

        return {
            "safe": len(findings) == 0,
            "findings": findings
        }


if __name__ == "__main__":
    test_safe = "api_key = os.getenv('API_KEY')"
    test_unsafe = "openai_key = 'sk-proj-abcdefghijklmnopqrstuvwxyz1234567890abcdef'"

    print("Safe check:", SecurityScanner.scan_code(test_safe))
    print("Unsafe check:", SecurityScanner.scan_code(test_unsafe))
