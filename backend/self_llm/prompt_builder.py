def build_prompt(architecture, hint):
    frontend = '\n'.join(architecture.get('frontend_components', []))
    engines = '\n'.join(architecture.get('backend_engines', []))
    services = '\n'.join(architecture.get('services', []))
    endpoints = '\n'.join(architecture.get('api_endpoints', []))
    data_roots = '\n'.join(architecture.get('data_roots', []))
    prompt = f"""
You are improving a biomedical research software platform.

Goal:
Increase probability that 25 out of 50 medical research facilities would consider buying it.

Architecture map:

FRONTEND COMPONENTS
{frontend}

BACKEND ENGINES
{engines}

SERVICES
{services}

API ENDPOINTS
{endpoints}

DATA ROOTS
{data_roots}

Focus improvements on:
- institutional credibility
- clinical traceability
- audit trails
- reproducibility
- workflow clarity
- evidence validation

Optional developer hint:
{hint}

Return structured proposal with these exact sections:
TITLE
PROBLEM
PROPOSAL
FILES_TO_CHANGE
EXPECTED_IMPACT
INSTITUTIONAL_VALUE
"""
    return prompt
