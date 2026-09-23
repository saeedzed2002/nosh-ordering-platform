# Versioned API artifacts

`openapi-v1.json` is the checked-in contract for the public Nosh `/api/v1`
surface. It is generated from the FastAPI application, not hand-edited.

Regenerate it after an intentional contract change:

~~~powershell
Set-Location backend
uv run python scripts/export_openapi.py
~~~

Then regenerate the frontend types from the same snapshot:

~~~powershell
Set-Location ../frontend
npm run generate:api
~~~

CI verifies that neither artifact drifts from its source. A change to an
existing v1 response or validation rule is a compatibility decision: update
the contract notes and use an additive route or a future API version when a
consumer would otherwise break.
