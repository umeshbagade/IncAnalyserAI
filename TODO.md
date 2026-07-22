# Integration Task: Move mockData from Frontend to Backend

## Steps
- [x] Step 0: Read all relevant files (frontend pages, API, backend, components)
- [x] Step 1: Create `backend/app/mockData.ts` (reference copy of frontend mockData)
- [x] Step 2: Delete `frontend/src/data/mockData.ts`
- [x] Step 3: Verify frontend no longer has any imports from mockData
- [x] Step 4: Update `README.md` with note about data flow change (API only)

## Summary of Changes

### Files Created
- `backend/app/mockData.ts` — Reference copy of the TypeScript data contract (mirrors frontend types)

### Files Deleted
- `frontend/src/data/mockData.ts` — Mock data moved to backend
- `frontend/src/data/` (empty directory removed)

### Files Modified
- `README.md` — Updated project structure to reflect removal of `data/mockData.ts`

### Data Flow (No Code Changes Needed)
The frontend was ALREADY fully integrated with the backend API:
- `page.tsx` uses `getIncidents()` + `getDashboardStats()` from `@/lib/api`
- `inc/[id]/page.tsx` uses `getIncidentDashboard()`, `getEvidence()`, `submitEvidenceFeedback()` from `@/lib/api`
- `api.ts` proxies through Next.js rewrites (`next.config.js`) → `http://localhost:8000/api/*`
- Backend `main.py` + `data.py` serve all data via REST endpoints

