"""Deterministic mock responses — used when GOOGLE_API_KEY is not configured.

Keeps the multi-agent flow (routing → parallel specialists → aggregation)
fully testable and demo-able without a real LLM key.
"""

MOCK_LAW_ANALYSIS = (
    "Mock legal analysis: based on general contract and business law principles, "
    "this question raises potential liability exposure that should be reviewed "
    "against the relevant statutes and case law for the applicable jurisdiction."
)

MOCK_TAX_ANALYSIS = (
    "Mock tax analysis: potential civil penalties under IRC §§ 6651/6662, possible "
    "criminal exposure under 18 U.S.C. § 7201, IRS/DOJ enforcement, and FBAR/FATCA "
    "reporting obligations if offshore accounts are involved. Educational purposes only."
)

MOCK_COMPLIANCE_ANALYSIS = (
    "Mock compliance analysis: this may fall under SEC/SOX/FCPA/AML jurisdiction "
    "depending on the facts, with administrative, civil, or criminal remedies "
    "available to regulators. Voluntary disclosure and remediation are mitigating "
    "factors. Educational purposes only — consult a licensed attorney."
)


def mock_aggregate(sections: list[str]) -> str:
    """Mock synthesis: join sections with a closing disclaimer."""
    body = "\n\n---\n\n".join(sections)
    disclaimer = (
        "\n\n---\n\n*This response was generated in mock mode (no GOOGLE_API_KEY "
        "configured) and is for educational/demo purposes only.*"
    )
    return body + disclaimer
