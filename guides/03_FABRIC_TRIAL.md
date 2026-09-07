# Microsoft Fabric trial + authenticated semantic-model runtime test

## Goal
Create an isolated Fabric trial workspace, load the canonical fixture into a Lakehouse Delta table named `SaCFact`, create a Direct Lake semantic model containing that table, apply the generated TMDL measures, and execute the ten query intents through the Power BI DAX Execute Queries API.

Official docs:
- Trial: https://learn.microsoft.com/en-us/fabric/get-started/fabric-trial
- Create semantic model: https://learn.microsoft.com/en-us/fabric/data-warehouse/create-semantic-model
- TMDL semantic model definition: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/semantic-model-definition
- Update definition: https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/update-semantic-model-definition
- DAX Execute Queries: https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries

## A. Start the Fabric trial
1. Sign in to https://app.fabric.microsoft.com with a work/school Microsoft account.
2. Open the account manager (profile icon, upper right).
3. Choose **Start trial**. Microsoft currently documents a 60-day Fabric trial. If the option is absent, your tenant administrator may have disabled trials or the tenant may have exhausted trial capacity.
4. Create a new workspace and assign **Fabric Trial** as the workspace type/capacity.

If you do not already have a Power BI per-user license, Microsoft documents that a Fabric free license can be used to start the trial flow.

## B. Create a Lakehouse and load the exact fixture
1. In the trial workspace, create a **Lakehouse** named `SaCConformanceLakehouse`.
2. In the Lakehouse `Files` area upload this kit's `data/fixture.csv` as `fixture.csv`.
3. Create a Fabric Notebook attached to that Lakehouse.
4. Paste/run `platform_setup/fabric_load_fixture_notebook.py`.
5. Confirm the notebook prints `SaCFact rows: 12` and visually inspect the rows.

Do not let Power Query or automatic inference alter the types: the notebook specifies them explicitly.

## C. Create a Direct Lake semantic model
Microsoft no longer creates default semantic models automatically for new Lakehouses/Warehouses. Create one explicitly:
1. Open the Lakehouse or its SQL analytics endpoint.
2. Choose **New semantic model**.
3. Name it `SaC Conformance Model`.
4. Select the `SaCFact` table and confirm.
5. Open the model once and verify `SaCFact` is visible.

## D. Install Azure CLI and sign in (recommended auth for trial testing)
The test kit supports delegated user authentication via Azure CLI, avoiding a service-principal setup for a personal trial.

Install Azure CLI using Microsoft's instructions, then:
```bash
az login
az account show
```
If you have multiple tenants/subscriptions, make sure the logged-in identity is the same identity that owns/has access to the Fabric trial workspace.

Set in `.env`:
```text
FABRIC_AUTH_MODE=azure_cli
FABRIC_WORKSPACE_ID=
FABRIC_SEMANTIC_MODEL_ID=
FABRIC_TABLE_NAME=SaCFact
FABRIC_APPLY_TMDL=false
```
`FABRIC_TENANT_ID`, client ID, and secret are not required in `azure_cli` mode.

## E. Discover workspace and semantic-model IDs
```bash
python scripts/fabric_discover.py
```
First run: copy the workspace ID into `.env` as `FABRIC_WORKSPACE_ID`.
Run again. It will list semantic models in that workspace. Copy the `SaC Conformance Model` ID into `FABRIC_SEMANTIC_MODEL_ID`.

## F. Tenant setting for Execute Queries
The DAX Execute Queries API requires the tenant setting **Dataset Execute Queries REST API** to be enabled. Your user also needs read/build permission on the semantic model. If this is disabled and you are not the tenant admin, ask the Power BI/Fabric administrator to enable it for your test user/security group.

## G. Preflight
```bash
python scripts/00_preflight.py fabric
```
This fetches the semantic model definition. It should end `PRECHECK PASSED`.

## H. Preview the generated TMDL patch
```bash
python scripts/03_compile_artifacts.py
python scripts/05_run_platform.py fabric --deploy
```
With `FABRIC_APPLY_TMDL=false`, this is **preview only**. Inspect:
- `generated/fabric/fabric_measures_patch.tmdl`
- `generated/fabric_patched_table_preview.tmdl`

The preview adds calculated month/ISO-week columns and the generated measures. It does not replace your source table.

## I. Apply the patch and execute the runtime tests
After reviewing the preview, set:
```text
FABRIC_APPLY_TMDL=true
```
Then run:
```bash
python scripts/05_run_platform.py fabric --deploy
python scripts/11_runtime_query_validation.py fabric
```
The adapter uses the Fabric `updateDefinition` endpoint and then the Power BI `executeQueries` endpoint for DAX.

## J. Evidence produced
- `results/fabric_deployment.json`
- `results/fabric_raw.json` — exact DAX + raw response
- `results/fabric.json` — normalized observations
- `generated/fabric_patched_table_preview.tmdl`
- `observability/events.ndjson`

## K. Access-governance test
For a basic governance test, use two identities or workspace/model permission states:
1. Authorized user with semantic-model Build/read permission: run query and record success.
2. Unauthorized user with Build/read removed: run the same query and record HTTP/permission failure.

If you use RLS, the Execute Queries API supports impersonation subject to documented limitations. Keep this separate from the base portability test so an authentication-policy issue is not misclassified as metric divergence.

## L. Service-principal alternative
If your organization prefers application auth:
```text
FABRIC_AUTH_MODE=service_principal
FABRIC_TENANT_ID=<tenant>
FABRIC_CLIENT_ID=<app id>
FABRIC_CLIENT_SECRET=<secret>
```
Your tenant/admin must allow the relevant Fabric/Power BI APIs and grant workspace/model permissions. Service-principal/RLS scenarios have additional restrictions, so delegated user auth is simpler for the trial experiment.
