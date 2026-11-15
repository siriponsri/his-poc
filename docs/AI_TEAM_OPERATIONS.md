# AI evidence, team responsibility and operations

Use these workflows to review prepared work, give each task an accountable owner
and inspect AI processing. Sign in with your own account and confirm the patient,
visit and facility before acting. Available profiles and task controls come from
current server permissions; choosing a filter or profile does not grant access.

This guide describes the implemented interface for the synthetic POC. It does
not declare live acceptance complete or establish clinical effectiveness. Use
**User Guide** in the app for the wider department workflows.

## Review the evidence before using a draft

1. Open **Workspace → Prepared work** and choose the appropriate **ทีมงาน** /
   **Preparation for** profile. Select the prepared visit you intend to review.
2. Read **Evidence coverage** before interpreting the draft. Expand
   **ดูข้อมูลที่ใช้และที่ยังไม่รวม** to see included, eligible and omitted sources
   by kind, partial-source counts and omitted-source labels/reasons. These counts
   describe the permitted sources collected for that preparation, not every
   record in the hospital.
3. Click a source title beside **At a glance**, **งานที่ควรตรวจต่อ**, or a draft's
   source references. **Source snapshot** opens the captured source used by that
   preparation. A quoted fact highlights its exact passage; a typed-field fact
   highlights the corresponding field. The dialog's scrollable reading region
   supports keyboard focus, and Escape closes it.
4. Compare the highlighted evidence with the complete captured source. When a
   document was partly selected, **ช่วงข้อความที่ใช้เตรียมร่าง** shows the exact
   model-visible passage. The complete captured document can contain text the
   model did not receive. Metadata-only profiles have no document body to display.
5. Review the draft's meaning, then select only the actions you intend to save.
   Suggested action checkboxes start selected. Clear unwanted actions before
   **ใช้ร่างและสร้างงานที่เลือก** / **Use draft & create selected follow-ups**.
   Read the resulting **รายการที่บันทึก** / **Saved workflow items** and open the
   saved document or task to confirm its actual state.

Partial selection and omission are different: a partial source contributes an
exact bounded passage; an omitted source contributes no content to that model
input. Neither proves that a document, test or clinical fact is missing from the
patient's record. Read the remaining permitted records when they matter.

The snapshot is historical evidence, not a replacement for the current record.
If it says **ฉบับอ้างอิงเดิม บริบทที่ใช้เตรียมร่างเปลี่ยนแล้ว**, the whole
preparation context has changed. The opened record itself may be unchanged;
compare current sources before proceeding. Saving rechecks current source, revision and permission
bindings; changed evidence can block use of the old draft. If an edit is held on
the page, decide whether to use the permitted bound workflow or
**ทิ้งการแก้ไขและอ่านล่าสุด** before switching work.

**ตรวจคำอ้างอิงกับต้นฉบับ** checks quoted text or a typed field against its source.
It is not a clinical accuracy score. Source references attached to a draft are
per-source attribution; they do not certify every sentence's meaning. Check
negation, who a statement concerns, analyte/value/unit associations and whether
the draft introduces a diagnosis, urgency, treatment or unsupported missingness.
Records readiness stays metadata-only; selecting another profile does not give a
nursing account laboratory access. Saving a prepared D22 draft does not sign a
D06 handover, release a laboratory result or approve clinical care.

To prepare one new visit, expand **การรับบริการที่เตรียมได้** / **Eligible visits**,
identify the exact visit and use its **เตรียม** / **Prepare** button. The separate
**เตรียมงานของฉัน** / **Prepare my work** action prepares a batch. Reading a run,
opening a snapshot or refreshing the worklist does not request a new generation.
Enable a watch only when you deliberately want that separate bounded workflow.

## Assign and follow up work in Team queue

Open **Team queue** from the sidebar or the Workspace heading. Choose **Team**,
**My work** or **Unassigned**, then search or filter by workspace and status.
Search and pagination read the authorized server queue. Top counts describe
authorized **active** work under the current search/workspace, before the
ownership-view and status filters. A Completed table filter therefore does not
turn those active-work counts into completed-work counts.

Select a task to open its full-width **Task responsibility** section. Check its
patient, visit, current owner, version and state. **Open patient record** opens the
read-only patient panel; **Open workspace** returns to the task's domain workflow.

| Intended action | Control | Expected result |
|---|---|---|
| Take an unassigned task | **รับผิดชอบงานนี้** | You become the owner; the task remains the same obligation and state. |
| Return your task to the team | **คืนงานให้ทีม** | Your ownership is removed when the server permits release. |
| Hand work to a colleague | **ส่งต่องาน** | Choose **ผู้รับผิดชอบคนใหม่**, enter **เหตุผลส่งต่องาน**, then confirm. |
| Set or change follow-up timing | **กำหนดงาน** | Save a due date/time and low, normal or high operational priority. Leave the date blank to clear it. |
| Follow up overdue active work | **ยกระดับการติดตาม** | Enter a reason and confirm the next tracking level, up to level 3. |

The handoff selector contains only colleagues currently eligible for that task's
organization, facility, domain, credentials and patient scope. If it is empty,
check the assignment with the responsible administrator; do not substitute an
unrelated account. A handoff reason should explain what remains to do. Assigning
a task does not transfer the sender's actor-owned AI run or grant patient access.

The date input explicitly shows the device's time zone. Confirm that time zone
before saving. Priority and due dates organize work; they are not medical triage
or an inferred urgency rating. Escalation retains the same task and owner and
records a reason. It does not send an email/SMS, create a second obligation or
complete the work. Ownership, scheduling and escalation alone do not request AI
preparation or change the underlying clinical source identity.

Use **สถานะงานและประวัติ** for the original task's status controls/history, or
continue through its domain. Order tasks still require their domain actions;
AI-review completion still requires the applicable review/commit workflow. Claim,
handoff and escalation cannot bypass those completion guards. Completed or
cancelled tasks do not accept coordination changes.

If a task changes while you work, use **อ่านงานนี้ล่าสุด**, compare the latest
owner/version and start a new action only after review. If the outcome is unknown,
keep the current command/context and use **ตรวจผลคำสั่งเดิม**. That control retries
the identical body and idempotency key to confirm the original operation. Do not
create another handoff or task to work around an unconfirmed request.

## Inspect processing in Administration → AI operations

This read-only tab requires current **D34.read** and **identity.admin** permissions
in the active facility. It presents operational metadata without opening patient
charts, source bodies or model drafts. Administration does not confer clinical
signing authority.

1. Open **AI operations**. Read the observation time and facility scope.
2. Interpret the counters using the definitions below. Expand **สถานะตามโปรไฟล์**
   for per-profile counts.
3. Filter **Preparation** and **Execution**, then use **ก่อนหน้า** / **ถัดไป** for
   server-side pages. These filters affect the row table; the top counters still
   summarize all recorded runs in the authorized facility.
4. Open a row's **รายละเอียด** to read its recorded error, times, token usage,
   source coverage, revision count, saved-effect count and measured cost. Use
   **อ่านสถานะล่าสุด** for an explicit metadata refresh. While work is queued or
   running, the visible tab also refreshes metadata periodically.

| Counter | Recorded states included |
|---|---|
| Waiting | Queued and waiting for capacity |
| Preparing | Running |
| Needs review | Awaiting human review |
| Needs attention | Failed, timed out, invalid output, abstained and interrupted |

**Source changed** remains a distinct execution/review condition in the table;
the attention total is not a count of every non-success state.

**Declared configuration** reports configured/enabled settings and profiles the
operator declared. It does not probe the live model or qualify a newly changed
input selector. Live model status remains **ยังไม่ได้ตรวจ**. **Worker activity**
shows **Heartbeat: ยังไม่มีข้อมูลยืนยัน**: last-started and last-completed times are
historical activity, not proof that a worker is healthy or running now.

An unmeasured cost, token count or duration remains **ยังไม่วัด** / null; it is not
zero or free. Source coverage reports counts, not clinical correctness. Evidence
freshness is not checked in this Admin view. The tab offers no generation,
retry/cancel, provider probe, host control or clinical-signing action; investigate
an issue through the appropriate authorized workflow.

For API, transaction and version details, see the
[engineering contract](AI_TEAM_OPERATIONS_CONTRACT.md). Runtime validation and
release evidence must state their own tested scope and results separately.
