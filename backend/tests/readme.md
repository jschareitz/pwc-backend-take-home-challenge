# Testfälle (KI-generierte readme.md)
## Kurzfassung der implementierten Tests

- Unit-Tests: pruefen Service-Logik isoliert (Metrik-Mapping, Not-Found, Delete-Regeln je Status).
- API-Tests: pruefen Request-Validierung und korrektes Exception-Mapping auf HTTP-Codes (422/404/409/500).
- Integrationstests: pruefen Kernflows ueber mehrere Schichten (Job erstellen/lesen/loeschen, Metriken, Validierung).
- E2E-Tests: pruefen echtes Zusammenspiel von API, DB und Worker im Compose-Setup (Verarbeitung + Row-Locking).
- Load-Test: erzeugt viele Jobs parallel und prueft, dass alle sauber angelegt und bis zum Endstatus verarbeitet werden.

## Ausfuehren nach Ebene

- Alle Tests: `uv run pytest -q`
- Nur Unit-Tests: `uv run pytest -q -m unit`
- Nur API-Tests: `uv run pytest -q -m api`
- Nur Integration-Tests: `uv run pytest -q -m integration`
- E2E- und Load-Tests lassen sich mit Docker Compose starten

## E2E-Compose-Stack

- Bevorzugter Startbefehl:\
   `docker compose -p e2e_test -f docker-compose.e2e.yml up --abort-on-container-exit --exit-code-from test`
- Mit optionalem Rebuild (nur noetig bei Code-/Dockerfile-Aenderungen):\
   `docker compose -p e2e_test -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from test`
- E2E-Pytest verwendet `BASE_URL` und startet/stoppt Docker nicht selbst.
- Die E2E-Compose-Datei ist eigenstaendig und wird nicht mit der Dev-Compose-Datei gemerged.
- Standard: Es wird 1 Worker gestartet.
- Optionales Worker-Scaling (Beispiel mit 4 Workern):\
   `docker compose -p e2e_test -f docker-compose.e2e.yml up --abort-on-container-exit --exit-code-from test --scale worker=4 test`

## Load-Compose-Stack

- Bevorzugter Startbefehl:\
   `docker compose -p load_test -f docker-compose.load.yml up --abort-on-container-exit --exit-code-from load_test`
- Mit optionalem Rebuild (nur noetig bei Code-/Dockerfile-Aenderungen):\
   `docker compose -p load_test -f docker-compose.load.yml up --build --abort-on-container-exit --exit-code-from load_test`
- Aufraeumen:\
   `docker compose -p load_test -f docker-compose.load.yml down -v`
- Standard: Es wird 1 Worker gestartet.
- Optionales Worker-Scaling (Beispiel mit 4 Workern):\
   `docker compose -p load_test -f docker-compose.load.yml up --abort-on-container-exit --exit-code-from load_test --scale worker=4`
- Wichtige Parameter (optional):
   - `LOAD_REQUESTS` (Standard: `500`)
   - `LOAD_CONCURRENCY` (Standard: `50`)
   - `LOAD_TIMEOUT_SECONDS` (Standard: `300`)

## Testfall-Zusammenfassung

### Unit (`tests/unit/test_services_unit.py`)

- `test_metrics_service_maps_aggregate_row_to_response_dict`:\
   Prueft das Mapping der aggregierten DB-Werte auf das erwartete Metrics-Response-Dict.
- `test_metrics_service_defaults_avg_to_zero_when_none`:\
   Stellt sicher, dass `average_processing_duration_seconds` bei `None` als `0.0` zurueckkommt.
- `test_delete_job_deletes_when_pending`:\
   Verifiziert: Pending-Job darf geloescht werden, `delete()` + `commit()` werden ausgefuehrt.
- `test_delete_job_rejects_when_already_started_or_finished`:\
   Verifiziert: Nicht-pending Jobs (processing/completed) duerfen nicht geloescht werden (`JobAlreadyStartedException`).
- `test_get_job_raises_not_found_exception`:\
   Verifiziert: Fehlender Job fuehrt zu `JobNotFoundException`.

### API (`tests/api/test_routes_validation_and_exceptions.py`)

- `test_create_job_rejects_out_of_range_retries`:\
   Input-Validierung fuer `max_retries` (ausserhalb erlaubter Grenzen) liefert HTTP 422.
- `test_get_job_with_invalid_uuid_returns_422`:\
   Ungueltige UUID im Pfad liefert HTTP 422.
- `test_route_maps_job_not_found_to_404`:\
   Domain-Exception `JobNotFoundException` wird korrekt auf HTTP 404 gemappt.
- `test_route_maps_already_started_delete_to_409`:\
   Domain-Exception `JobAlreadyStartedException` wird korrekt auf HTTP 409 gemappt.
- `test_route_maps_sqlalchemy_error_to_500`:\
   DB-Fehler (`SQLAlchemyError`) wird als HTTP 500 mit stabiler Fehlermeldung zurueckgegeben.

### Integration (`tests/integration/test_critical_flows.py`)

- `test_create_and_get_job_happy_path`:\
   End-to-end innerhalb der App-Schichten: Job erstellen und wieder abrufen.
- `test_get_missing_job_returns_404`:\
   Nicht vorhandene Job-ID liefert HTTP 404.
- `test_delete_pending_job_returns_204_and_removes_job`:\
   Pending-Job loeschen liefert 204; anschliessendes GET bestaetigt tatsaechliches Entfernen.
- `test_delete_non_pending_job_returns_409`:\
   Loeschen eines bereits gestarteten Jobs wird mit HTTP 409 abgewiesen.
- `test_metrics_returns_expected_aggregates`:\
   Prueft Zaehler (total/pending/processing/completed/failed) sowie Durchschnittsdauer fuer completed Jobs.
- `test_empty_payload_is_rejected_with_422`:\
   Leeres Payload wird durch Validierung abgewiesen (HTTP 422).

### E2E (`tests/e2e/`)

- `test_worker_e2e.py::test_job_is_processed_by_worker_e2e`:\
   Verifiziert im Docker-Stack, dass ein angelegter Job vom Worker in einen Endzustand (`completed`/`failed`) ueberfuehrt wird.
- `test_row_lock_e2e.py::test_row_level_lock_skip_locked_allows_only_one_claimer`:\
   Verifiziert Row-Level-Locking mit `FOR UPDATE SKIP LOCKED`: nur ein Worker kann denselben Job gleichzeitig claimen.

### Load (`tests/e2e/test_load_e2e.py`)

- `test_job_submission_and_processing_under_load`:\
   Erzeugt viele Jobs parallel per API, prueft erfolgreiche Erstellung und wartet ueber Metriken darauf, dass alle Jobs in einem Endstatus (`completed`/`failed`) ankommen.