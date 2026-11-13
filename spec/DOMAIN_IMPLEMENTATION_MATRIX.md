# เมทริกซ์การพัฒนา HIS ครบ 38 domains

**เป้าหมายใหม่:** แอปพัฒนาระบบเต็มที่ใช้งานต่อเนื่องกัน มี login, PostgreSQL และ workflow ของแต่ละ domain จริง ภายใน modular monolith เดียว ไม่หยุดที่ 38 เมนูหรือฟอร์ม JSON กลางชุดเดียว

เอกสารนี้เป็นข้อกำหนดงาน ยังไม่ได้สร้าง instance หรือรับรองว่า feature ทำแล้ว ชื่อ/รหัสตรง v0.2.0 ซึ่งมี 32 planned และ 6 integration-planned; ทุกหน้า domain เดิมเป็น placeholder แม้หก domain มี shared-core demo บางส่วน

## ระดับและสถานะ

- **L2 ทุก domain:** list/detail/form เฉพาะงาน + workflow ที่บันทึก PostgreSQL จริง มีสิทธิ์ state transition, validation, audit, tests และเปิดกลับหลัง restart ได้
- **L3:** journeys J01–J10 ตรง FULL_SYSTEM_SPEC_TH.md เชื่อม identity/context/transactions จริง ไม่ใช่เพียงลิงก์หน้าจอ
- **L4 แยก:** connector ภายนอกที่ตรวจ endpoint/protocol/authorization จริง; UNKNOWN ภายนอกไม่บล็อก manual/export/local-adapter workflow
- รอบนี้เป็น functional development prototype ไม่ใช่ production/clinical certification หรือทุกฟีเจอร์ของทุกวิชาชีพ

JSON แยก `implementation_status`, `verified_level`, `verification_status`, `external_integration_status` ทุก domain เริ่ม PLANNED / L0 / NOT_RUN / NOT_CONNECTED สำหรับเป้าหมายใหม่นี้ ผล PASS ของ shared core เดิมไม่เลื่อนทั้ง domain เป็น L2

ปรับ AGENTS/GOAL/BACKLOG ให้รับเป้าหมายใหม่และยกเลิก singleton ในฐานะขอบเขตส่งมอบ โดยคง authorization, patient/encounter/task binding, version/hash/evidence approval, idempotency, audit, explicit mock และห้าม live fallback เงียบ ๆ

## ฐานและ acceptance ร่วม

ใช้ Organization/Site/Department, User/Role/Scope/Session, Patient/Identifier, Encounter และ Task ที่มี persisted domain/record binding; ไม่เชื่อ ID จาก browser เพียงอย่างเดียว มี PostgreSQL FK/unique/check constraints, actor/audit, DocumentVersion/StorageObject/hash และ migrations/DTO ที่ version ได้ แยก fixture viewer จากข้อมูลที่เขียนผ่าน API

ทุก domain ทดสอบ role/scope ผิด, stale version, invalid transition และ retry โดยไม่เกิด partial write; รองรับหลาย record โดยไม่ล้างฐานเดิม ใช้ UI primitives ร่วมได้ แต่มี entity, validation และ workflow เฉพาะงาน ราคาเก็บ version/snapshot; stock และ posted ledger เป็น transactional ใช้ Decimal และแยก billed/submitted/approved/gross_received/refunded/net_received/outstanding/cost

Clinical domains ใช้ข้อมูลสังเคราะห์และการตรวจยืนยันด้วยคน ไม่เพิ่มการคำนวณ dose, triage, blood compatibility หรือ diagnosis ที่ยังไม่ประเมิน API ด้านล่างคือ capability ที่ต้องทำ ไม่ใช่ endpoint ที่ประกาศว่า implement แล้ว รายการสถานะและ transition แบบ machine-readable อยู่ใน JSON คู่กัน

## งานขั้นต่ำราย domain

### D01 ทะเบียนและตัวตนผู้ป่วย

เดิม **planned** → เป้าหมาย **L2**; L3: J01, J04, J07, J10

- **หน้า:** ค้นหา/รายชื่อผู้ป่วย; แฟ้มตัวตนและ identifiers; ลงทะเบียน/แก้ไข/ตรวจยืนยัน
- **Workflow:** ลงทะเบียนผู้ป่วยหลายราย; สถานะ draft, verified, active, inactive
- **Entity/FK:** Patient(id,organization_id); PatientIdentifier(patient_id,issuer_id); PatientContact(patient_id) **Role:** registration, medical_records
- **API:** GET patients/search/detail; POST patients; PATCH draft/demographics with version; POST verify/activate/inactivate
- **กติกา:** Identifier ที่กำหนดเป็น unique ต้องไม่ซ้ำใน issuer; ห้ามลบผู้ป่วยที่มี encounter; ไม่ merge อัตโนมัติ
- **Acceptance:** สร้างผู้ป่วยสองราย ยืนยันและเปิดแฟ้มได้หลัง restart; identifier ซ้ำต้อง conflict และไม่เขียนครึ่งรายการ
- **เชื่อม:** D02/D03/D21 ใช้ patient_id เดียวกัน; D34 จำกัดองค์กรและสิทธิ์
- **ภายนอก:** MPI/ทะเบียนภายนอกและ assigning-authority mapping; ใช้ identifiers สังเคราะห์ของแอปก่อนได้

### D02 นัดหมาย คิว และความจุบริการ

เดิม **planned** → เป้าหมาย **L2**; L3: J01, J04, J10

- **หน้า:** ปฏิทินนัดและคิวบริการ; รายละเอียด slot/appointment; จอง/เลื่อน/เช็กอิน/เรียกคิว
- **Workflow:** นัดหมายเข้าสู่การรับบริการ; สถานะ requested, booked, checked_in, called, completed, cancelled
- **Entity/FK:** ServiceSlot(department_id,practitioner_id); Appointment(patient_id,slot_id); QueueTicket(appointment_id,encounter_id) **Role:** scheduler, registration, nurse
- **API:** GET slots/appointments/queues; POST book/reschedule/check-in/call/complete/cancel
- **กติกา:** ตรวจความจุ slot ใน transaction; check-in ซ้ำไม่สร้าง encounter/คิวซ้ำ
- **Acceptance:** ผู้ใช้สองคนจองที่นั่งสุดท้ายพร้อมกัน สำเร็จได้เพียงคนเดียว; check-in แล้วไป OPD ด้วย encounter เดิม
- **เชื่อม:** D01 patient → D03 encounter; D21 ส่งคำขอนัดผ่านสิทธิ์เจ้าของข้อมูล
- **ภายนอก:** SMS/ปฏิทิน/คิวภายนอก; เริ่มจาก in-app notification และคิวท้องถิ่น

### D03 OPD และเวชระเบียนการตรวจ

เดิม **planned** → เป้าหมาย **L2**; L3: J01, J02, J03, J08

- **หน้า:** รายชื่อ encounter OPD; หน้าเวชระเบียนและงานค้าง; บันทึกตรวจ/ปิด encounter
- **Workflow:** รับตรวจและสรุปการตรวจ; สถานะ waiting, in_consult, reviewed, completed, closed
- **Entity/FK:** Encounter(patient_id,department_id,practitioner_id); ConsultationNote(encounter_id,document_version_id); EncounterDisposition(encounter_id) **Role:** clinician, nurse, registration
- **API:** GET encounters/detail/timeline; POST encounter/start/note/review/complete/close
- **กติกา:** คำวินิจฉัยและแผนเป็นข้อมูลที่บุคลากรกรอก; context ต้องตรงผู้ป่วย; การปิดมีรายการงานค้างให้ยืนยัน
- **Acceptance:** เปิด encounter สองราย บันทึกแยกกัน สั่งตรวจและอ่านผลกลับในแฟ้มที่ถูกต้องหลัง reload
- **เชื่อม:** D07 orders, D10/D11 results, D22 documents, D23 charges ใช้ encounter_id ร่วม
- **ภายนอก:** EMR/terminology ภายนอก; ใช้ local synthetic codes ที่ระบุแหล่งได้

### D04 ห้องฉุกเฉิน

เดิม **planned** → เป้าหมาย **L2**; L3: J04

- **หน้า:** บอร์ดห้องฉุกเฉิน; รายละเอียดการประเมินและ disposition; ลงทะเบียนเหตุ/บันทึก triage/ส่งต่อ
- **Workflow:** รับฉุกเฉินและกำหนดปลายทางโดยผู้ใช้; สถานะ arrived, assessed, in_care, discharged, admission_requested, referral_requested
- **Entity/FK:** EmergencyEpisode(encounter_id); TriageAssessment(episode_id,assessor_id); EmergencyDisposition(episode_id) **Role:** triage_nurse, emergency_clinician
- **API:** GET emergency-board/episode; POST arrival/assessment/update/disposition
- **กติกา:** ระดับ triage และการตัดสินใจเป็น manual; ไม่สร้างคะแนน/diagnosis จาก AI; บันทึกฉบับและผู้ประเมิน
- **Acceptance:** บันทึก triage สังเคราะห์แล้วขอ admit สร้างคำขอ D05 ครั้งเดียว พร้อมประวัติเดิมตรวจย้อนหลังได้
- **เชื่อม:** D01/D03 identity/encounter → D05 admission หรือ D20 referral
- **ภายนอก:** EMS/ambulance และเกณฑ์โรงพยาบาล; endpoint ไม่จำเป็นต่อ manual workflow

### D05 ผู้ป่วยใน เตียง และการปิดการรับบริการ

เดิม **planned** → เป้าหมาย **L2**; L3: J04

- **หน้า:** ผังเตียงและ admission list; รายละเอียดการนอนโรงพยาบาล; รับเข้า/ย้ายเตียง/จำหน่าย
- **Workflow:** จัดเตียงและปิด admission; สถานะ requested, admitted, transfer_requested, discharge_ready, discharged
- **Entity/FK:** Admission(encounter_id); Bed(ward_id); BedAssignment(admission_id,bed_id); DischargeRecord(admission_id) **Role:** admission_officer, ward_nurse, clinician
- **API:** GET beds/admissions; POST admit/transfer/discharge-ready/discharge
- **กติกา:** เตียงมี active assignment ได้หนึ่งรายการ; ย้าย/จำหน่ายและคืนเตียงเป็น transaction; ห้ามรีเซ็ต encounter เก่า
- **Acceptance:** admit แข่งกันใช้เตียงเดียวต้องสำเร็จหนึ่งราย; ย้ายเตียงแล้วเตียงเก่าว่างและประวัติยังครบ
- **เชื่อม:** D04 admission request; D06 handover; D19 meal; D23 inpatient charges
- **ภายนอก:** Bed-management ภายนอก; ward/bed catalog สร้างในแอปได้

### D06 งานพยาบาลและการส่งเวร

เดิม **planned** → เป้าหมาย **L2**; L3: J04

- **หน้า:** worklist งานพยาบาล/ส่งเวร; care plan และ handover detail; บันทึกกิจกรรม/ลงนาม/รับเวร
- **Workflow:** ส่งเวรพร้อมงานค้าง; สถานะ draft, signed, acknowledged, amended
- **Entity/FK:** NursingCarePlan(encounter_id); NursingTask(plan_id,assignee_id); Handover(encounter_id,document_version_id,receiving_staff_id) **Role:** nurse, charge_nurse
- **API:** GET nursing-worklist/handover; POST care-task/complete/handover/sign/acknowledge/amend
- **กติกา:** รับเวรต้องเป็นผู้มีสิทธิ์; ฉบับลงนามคงเดิมและ amendment มีเหตุผล; ไม่ถือ task complete เท่ากับให้ยา
- **Acceptance:** พยาบาลเวรแรกส่งงานค้าง เวรถัดไปรับทราบแล้วเห็นงานเดิม ไม่มี task หายหรือถูกทำซ้ำ
- **เชื่อม:** D05 admission, D09 administration, D22 document versions และ D30 roster
- **ภายนอก:** Nursing/monitor systems; ใช้ manual entries และ local roster

### D07 คำสั่งแพทย์และการจัดการคำสั่ง

เดิม **planned** → เป้าหมาย **L2**; L3: J02, J03, J08

- **หน้า:** รายการคำสั่งแยกประเภท; order detail/status; สร้าง/ตรวจยืนยัน/แก้ไขด้วยฉบับใหม่/ยกเลิก
- **Workflow:** คำสั่งที่บุคลากรตรวจยืนยัน; สถานะ draft, signed, acknowledged, in_progress, completed, cancelled
- **Entity/FK:** ClinicalOrder(encounter_id,requester_id,catalog_item_id); OrderRevision(order_id); OrderTask(order_id,assignee_id) **Role:** clinician, authorized_order_receiver
- **API:** GET orders/catalog/status; POST draft/sign/acknowledge/start/complete/cancel
- **กติกา:** ไม่คำนวณขนาดยา/ข้อบ่งชี้อัตโนมัติ; signed order แก้ด้วย revision; ปลายทางตรวจ cancellation/version
- **Acceptance:** ลงคำสั่งแล็บและยาแล้วเกิด worklist ที่ถูกประเภท; retry ไม่สร้างคำสั่งซ้ำและยกเลิกตรวจย้อนหลังได้
- **เชื่อม:** D08 pharmacy, D10 lab, D11 imaging และ D23 charge source
- **ภายนอก:** e-prescription/order interfaces; manual synthetic orders ทำงานได้ในแอป

### D08 เภสัชกรรมและการจ่ายยา

เดิม **planned** → เป้าหมาย **L2**; L3: J03

- **หน้า:** คิวเภสัช/stock ที่จ่ายได้; prescription และ dispense detail; ตรวจทาน/จัดยา/ยืนยันจ่าย/คืน
- **Workflow:** จ่ายยาตามคำสั่งที่ตรวจโดยคน; สถานะ received, reviewed, prepared, dispensed, rejected, return_recorded
- **Entity/FK:** MedicationOrder(order_id); Dispense(medication_order_id,encounter_id); DispenseLine(item_id,lot_id,quantity); ReturnLine(dispense_line_id) **Role:** pharmacist, pharmacy_technician
- **API:** GET pharmacy-queue/dispense/eligible-lots; POST review/prepare/dispense/return
- **กติกา:** ตรวจยาด้วยผู้มีสิทธิ์; ไม่แนะนำ dose; quantity/lot/stock/charge ผูก transaction และห้ามติดลบ; การคืนสร้างรายการใหม่ผูก dispense line เดิม โดยยอดคืนสะสมไม่เกินยอดจ่ายที่ยังคืนได้; disposition ของยาคืนต้องมีผู้ตรวจและไม่เพิ่ม available stock อัตโนมัติ
- **Acceptance:** จ่ายจาก lot สังเคราะห์แล้ว stock ลด/charge เพิ่มครั้งเดียว; คืนอ้างอิงรายการเดิมและมี audit; ส่งคืนซ้ำหรือเกินยอดต้องถูกปฏิเสธ และของที่ยังไม่ผ่าน disposition ไม่กลับเข้า available stock
- **เชื่อม:** D07 order → D28 inventory movement → D23 charge; D09 อ่านรายการที่อนุมัติ
- **ภายนอก:** Drug catalog/barcode/robot; ใช้ synthetic formulary พร้อมหน่วยที่ระบุชัด

### D09 การให้ยา ณ จุดดูแล

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** MAR/worklist ตามเวลา; administration history; ยืนยันผู้ป่วย/บันทึกให้ยา/งด/แก้ไขเหตุการณ์
- **Workflow:** บันทึกการให้ยาที่ผู้ปฏิบัติยืนยัน; สถานะ scheduled, verified, administered, held, not_given, corrected
- **Entity/FK:** AdministrationTask(medication_order_id,encounter_id); AdministrationEvent(task_id,nurse_id); AdministrationCorrection(original_event_id) **Role:** nurse, authorized_witness
- **API:** GET mar/tasks/history; POST verify/administer/hold/not-given/correct
- **กติกา:** กรอก dose/time/route ตามคำสั่งด้วยคน; ไม่แปลงหน่วยหรือคำนวณยาอัตโนมัติ; event ซ้ำต้องป้องกัน
- **Acceptance:** บันทึกให้ยาหนึ่งครั้งแล้วส่งซ้ำไม่เพิ่ม event; รายการงดต้องมีเหตุผลและไม่แสดงว่า administered
- **เชื่อม:** D07 signed order, D08 dispense และ D06 nursing timeline
- **ภายนอก:** BCMA/pump; manual identity verification ใช้ได้โดยไม่เชื่อมอุปกรณ์

### D10 ห้องปฏิบัติการและผลวิกฤต

เดิม **integration-planned** → เป้าหมาย **L2**; L3: J02, J10

- **หน้า:** lab worklist/specimen list; accession และผลตรวจ; รับสิ่งส่งตรวจ/กรอกผล/ตรวจรับรอง/แก้ผล
- **Workflow:** manual laboratory result; สถานะ ordered, collected, received, preliminary, verified, released, corrected
- **Entity/FK:** LabRequest(order_id); Specimen(patient_id,encounter_id); Accession(specimen_id); LabResult(accession_id,analyte_id,unit_id,version) **Role:** specimen_collector, lab_technologist, lab_verifier
- **API:** GET lab-worklist/specimens/results; POST collect/receive/enter-result/verify/release/correct
- **กติกา:** ผล/หน่วย/reference เป็นข้อมูล manual; release ต้องตรวจสิทธิ์และ version; corrected result เก็บฉบับเดิม
- **Acceptance:** กรอกผล synthetic และ release แล้ว OPD เห็นผลของ encounter นั้น; correction แสดงทั้งฉบับเก่าและใหม่
- **เชื่อม:** D07 request → D03/D05 results → D22 report/D23 charge
- **ภายนอก:** LIS/analyzer/LOINC mapping; manual entry/release ไม่รอ endpoint

### D11 รังสี RIS และภาพทางการแพทย์

เดิม **integration-planned** → เป้าหมาย **L2**; L3: J08, J10

- **หน้า:** imaging worklist/ตารางนัด; study/files/report detail; อัปโหลดไฟล์สังเคราะห์/ร่างและรับรองรายงาน
- **Workflow:** รับภาพไฟล์และเผยแพร่รายงานโดยคน; สถานะ ordered, scheduled, acquired, report_draft, verified, released, amended
- **Entity/FK:** ImagingRequest(order_id); ImagingStudy(encounter_id); ImageAsset(study_id,storage_object_id,sha256); ImagingReport(study_id,document_version_id) **Role:** radiology_scheduler, radiographer, radiologist
- **API:** GET imaging-worklist/studies/files; POST schedule/upload/report/verify/release/amend
- **กติกา:** ไฟล์ allowlist/size/hash และ ownership ตรวจจริง; ไม่อ้าง PACS/DICOM conformance หรือวินิจฉัยจากภาพ
- **Acceptance:** แนบภาพสังเคราะห์กับ study แล้วเปิดจากแฟ้มถูกคน; release report ตามสิทธิ์และเข้าถึงไฟล์ข้ามคนไม่ได้
- **เชื่อม:** D07 request, D03/D05 chart, D22 documents และ D29 equipment availability
- **ภายนอก:** RIS/PACS/DICOM; L2 ใช้ local file storage พร้อม metadata ใน PostgreSQL

### D12 ห้องผ่าตัดและวิสัญญี

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** OR schedule/รายการผ่าตัด; case/checklist/บันทึกวิสัญญี; จองห้อง/ตรวจ checklist/บันทึกและปิด case
- **Workflow:** การจัดตารางและบันทึกหัตถการ; สถานะ requested, scheduled, checklist_verified, in_progress, documented, closed, cancelled
- **Entity/FK:** ProcedureCase(encounter_id,order_id); RoomReservation(room_id,case_id); ProcedureChecklist(case_id); AnesthesiaRecord(case_id,document_version_id) **Role:** or_scheduler, surgeon, anesthesia_clinician, or_nurse
- **API:** GET or-calendar/cases/checklists; POST schedule/check/record/close/cancel
- **กติกา:** ไม่ให้ dose/วิสัญญี recommendation; ห้อง/เวลาไม่ชน; checklist verification ต้องมี actor จริง
- **Acceptance:** จองห้องแล้วตรวจ checklist และปิด case เก็บเอกสารครบ; การจองชนกันถูกปฏิเสธ
- **เชื่อม:** D05 admission, D18 blood request, D31 instruments และ D23 charges
- **ภายนอก:** OR/anesthesia devices; manual documentation ไม่รอ device integration

### D13 ICU และข้อมูลจากอุปกรณ์

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** ICU patient/rounds worklist; observation timeline; กรอก observation/round note/ตรวจและส่งเวร
- **Workflow:** round และข้อมูลสังเกตแบบ manual; สถานะ draft, recorded, reviewed, signed, amended
- **Entity/FK:** ICUEpisode(admission_id); Observation(encounter_id,unit_id,observed_at); ICURound(episode_id,document_version_id); DeviceAssignment(episode_id,asset_id) **Role:** icu_nurse, intensivist
- **API:** GET icu-board/observations/rounds; POST observation/round/review/sign/amend
- **กติกา:** บันทึกค่าและหน่วยที่คนกรอก; ไม่สร้าง alarm/คะแนนวิกฤต/ตั้งอุปกรณ์อัตโนมัติ
- **Acceptance:** บันทึกหลายเวลาของผู้ป่วยสองคนแล้ว timeline ไม่ปน; แก้ค่าที่ลงนามต้องเป็นฉบับใหม่
- **เชื่อม:** D05 admission, D06 handover, D29 equipment และ D22 signed notes
- **ภายนอก:** Monitor/ventilator streams; manual observations เป็น workflow ท้องถิ่น

### D14 สูติกรรม มารดา และทารกแรกเกิด

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** ทะเบียน pregnancy/ตารางคลอด; maternal episode และ mother–child links; บันทึกครรภ์/คลอด/ยืนยันทารก
- **Workflow:** บันทึกการคลอดและเชื่อมตัวตนโดยผู้ใช้; สถานะ registered, antenatal_active, delivery_documented, verified, closed
- **Entity/FK:** PregnancyEpisode(mother_patient_id); DeliveryRecord(episode_id,encounter_id); ParentChildLink(mother_patient_id,child_patient_id); BirthRecord(child_patient_id) **Role:** obstetric_clinician, midwife, registration
- **API:** GET pregnancies/deliveries/links; POST episode/delivery/verify-link/close
- **กติกา:** อายุครรภ์/ผลการคลอดเป็น manual; การสร้างทารกและ link ต้อง atomic และ retry ไม่เพิ่มตัวตนซ้ำ
- **Acceptance:** บันทึกคลอดสังเคราะห์แล้วลงทะเบียนทารกหนึ่งราย ลิงก์แม่–ลูกคงอยู่หลัง restart และส่งซ้ำไม่สร้างลูกซ้ำ
- **เชื่อม:** D01 identities, D05 admission, D15 child follow-up และ D22 records
- **ภายนอก:** Birth registry/maternal reporting; บันทึกภายในได้ก่อนเชื่อมทะเบียน

### D15 กุมารเวชกรรมและการเติบโต

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** pediatric visit list; growth/immunization history; กรอก measurement/วัคซีนที่บันทึกด้วยคน/ทบทวน
- **Workflow:** ทบทวนข้อมูลเด็กตามครั้งรับบริการ; สถานะ draft, recorded, reviewed, closed, amended
- **Entity/FK:** PediatricVisit(encounter_id); GrowthMeasurement(patient_id,unit_id,measured_at); ImmunizationRecord(patient_id,encounter_id,item_id,lot_id) **Role:** pediatric_clinician, nurse
- **API:** GET child-history/growth/immunizations; POST measurements/records/review/close/amend
- **กติกา:** เก็บค่าดิบ/หน่วยและแสดงกราฟตามเวลา; ไม่คำนวณ dose/percentile หรือแนะนำวัคซีนโดยโมเดล
- **Acceptance:** เพิ่ม measurement ต่างวันแล้วกราฟ/history ใช้ค่าจริงจากฐาน; ฉบับแก้และผู้แก้ตรวจย้อนหลังได้
- **เชื่อม:** D14 parent-child link, D03 visit, D28 lot reference และ D22 note
- **ภายนอก:** Immunization registry/growth references; เริ่มด้วย raw measurement และ manual records

### D16 เวชศาสตร์ฟื้นฟูและกายภาพบำบัด

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** rehab referral/session calendar; แผนและ progress history; รับประเมิน/จัดแผน/นัดและบันทึก session
- **Workflow:** แผนฟื้นฟูและการติดตาม; สถานะ requested, assessed, active, reviewed, completed, discontinued
- **Entity/FK:** RehabReferral(order_id,encounter_id); RehabPlan(patient_id,therapist_id); TherapySession(plan_id,appointment_id); FunctionalAssessment(session_id) **Role:** rehab_clinician, physiotherapist, scheduler
- **API:** GET referrals/plans/sessions; POST assess/plan/schedule/session/review/complete
- **กติกา:** เป้าหมาย/แบบประเมินกรอกโดยคน; แผนมีรุ่นและผู้รับผิดชอบ; ไม่อ้างผลการรักษาจาก mock
- **Acceptance:** รับ referral จัดสาม session บันทึกผลแต่ละครั้งแล้วปิดแผนโดยไม่ลบ progress เดิม
- **เชื่อม:** D07 referral/order, D02 scheduling, D03 chart และ D23 session charges
- **ภายนอก:** Rehab devices/assessment instruments; เลือกแบบ manual ที่สิทธิใช้งานยืนยันแล้ว

### D17 ทันตกรรมและคลินิกเฉพาะทาง

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** dental/specialty appointment list; tooth chart/แผนหัตถการ; บันทึกตำแหน่ง/เสนอแผน/ยืนยันทำ
- **Workflow:** หัตถการตามแผนที่บุคลากรเลือก; สถานะ draft, reviewed, scheduled, performed, verified, closed, cancelled
- **Entity/FK:** SpecialtyVisit(encounter_id); DentalChart(patient_id,version); ToothFinding(chart_id,tooth_code); DentalProcedure(order_id,tooth_code) **Role:** dentist, specialty_clinician, dental_assistant
- **API:** GET specialty-visits/charts/plans; POST finding/plan/schedule/perform/verify/close
- **กติกา:** ตำแหน่งและหัตถการเลือกด้วยคน; ไม่ทำ diagnosis/plan อัตโนมัติ; chart edits มี version
- **Acceptance:** บันทึกคนละตำแหน่งในสอง visit แล้วเปิด chart ย้อนหลังถูกฉบับ และค่าบริการผูก procedure ถูกตัว
- **เชื่อม:** D01/D03 identity/encounter, D02 appointments และ D23 charges
- **ภายนอก:** Dental imaging/terminology; ใช้ manual chart และรหัส synthetic ที่ประกาศชัด

### D18 ธนาคารเลือดและการให้เลือด

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** blood requests/unit inventory; unit trace และการตรวจโดยผู้มีสิทธิ์; ร้องขอ/จอง/บันทึกผลตรวจ/อนุมัติปล่อย
- **Workflow:** ติดตามถุงเลือดโดยยืนยัน compatibility ด้วยคน; สถานะ requested, reviewed, reserved, compatibility_verified, released, administration_recorded, cancelled
- **Entity/FK:** BloodRequest(order_id,encounter_id); BloodUnit(unit_identifier,lot_id,expiry_at,eligibility_status,version); UnitReservation(request_id,unit_id); CompatibilityVerification(reservation_id,verifier_id,patient_id,request_version,unit_version,evidence_ref); TransfusionEvent(unit_id,encounter_id) **Role:** blood_bank_staff, authorized_verifier, transfusion_nurse
- **API:** GET requests/units/trace; POST review/reserve/manual-verification/release/record-event
- **กติกา:** ห้ามคำนวณ blood compatibility หรือปล่อยจาก AI; unit จองซ้อนไม่ได้; verification ผูก patient/request/unit revision และหลักฐานของผู้ตรวจ; ก่อน release ตรวจ expiry/quarantine/recall flags ที่บันทึกไว้และ eligibility ตาม policy โดย transaction เดียวกัน; ถ้าข้อมูลที่ใช้ยืนยันเปลี่ยนต้องตรวจใหม่
- **Acceptance:** จอง unit เดียวพร้อมกันต้องได้หนึ่งคำขอ; ผู้ตรวจยืนยันแล้วปล่อยและตามกลับผู้รับ/lot ได้; ถ้า unit หมดอายุ ถูก quarantine/recall หรือ revision เปลี่ยนหลัง verification ต้อง release ไม่ได้และไม่มี partial write
- **เชื่อม:** D07 request, D12 procedure, D05 admission และ D28 lot trace
- **ภายนอก:** Blood-bank/analyzer/hemovigilance; local synthetic unit trace ไม่อ้าง clinical compatibility validation

### D19 โภชนาการและอาหารผู้ป่วย

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** diet/meal worklist; diet order และรอบส่งอาหาร; กรอกแผนโดยคน/ตรวจ/เตรียม/ยืนยันส่ง
- **Workflow:** อาหารตามคำสั่งที่ตรวจแล้ว; สถานะ ordered, reviewed, prepared, delivered, cancelled
- **Entity/FK:** DietOrder(encounter_id,author_id); NutritionReview(order_id,dietitian_id); MealDispatch(order_id,meal_period,ward_id) **Role:** dietitian, ward_nurse, kitchen_staff
- **API:** GET diet-orders/meal-rounds; POST order/review/prepare/deliver/cancel
- **กติกา:** ข้อจำกัดและอาหารเป็น manual; แสดงข้อมูลแพ้ที่บันทึกไว้โดยไม่แนะนำอาหารเอง; รอบส่งมี unique key
- **Acceptance:** เปลี่ยน diet ก่อนรอบเตรียมแล้วครัวเห็นฉบับล่าสุด; ยืนยันส่งซ้ำไม่เพิ่มมื้อและรายการยกเลิกไม่ถูกเตรียม
- **เชื่อม:** D05 ward/bed, D03 clinical context และ D06 nursing acknowledgement
- **ภายนอก:** Nutrition/food vendors; local preparation/delivery log ทำงานได้เอง

### D20 การส่งต่อและการติดตามผล

เดิม **integration-planned** → เป้าหมาย **L2**; L3: J04, J08, J10

- **หน้า:** referral worklist; ปลายทาง/เอกสาร/response history; ร่าง/ตรวจ/สร้างไฟล์ส่งออก/บันทึกตอบกลับ
- **Workflow:** เตรียมส่งต่อและติดตามหลักฐาน; สถานะ draft, reviewed, exported, response_recorded, closed, cancelled
- **Entity/FK:** Referral(encounter_id,destination_org_id); ReferralDocument(referral_id,document_version_id); ReferralResponse(referral_id,source_type,attachment_id) **Role:** clinician, referral_coordinator
- **API:** GET referrals/detail/export-status; POST draft/review/export/record-response/close
- **กติกา:** exported ไม่เท่ากับ remote received; response manual ต้องมีแหล่ง/ผู้บันทึก; ไม่ส่งข้อความนอกระบบเอง
- **Acceptance:** สร้าง referral packet จากฉบับเอกสารที่เลือก ดาวน์โหลดได้และสถานะยังแสดงว่ายังไม่ยืนยันการรับจากภายนอก
- **เชื่อม:** D04/D03 disposition, D22 versioned documents และ D35 connector status
- **ภายนอก:** Referral network/FHIR/transport; local export และ manual response ใช้งานได้โดยไม่รอ endpoint

### D21 พอร์ทัลและการเข้าถึงของผู้ป่วย

เดิม **planned** → เป้าหมาย **L2**; L3: J10

- **หน้า:** portal login/รายการนัดและผลของตน; encounter/result ที่อนุญาตเผยแพร่; ขอนัด/ขอแก้ข้อมูล/ติดตามคำขอ
- **Workflow:** ผู้ป่วยส่งคำขอนัดของตน; สถานะ requested, reviewed, booked, completed, cancelled, declined
- **Entity/FK:** PortalIdentity(user_id,patient_id); PortalAppointmentRequest(patient_id,slot_id); PortalCorrectionRequest(patient_id,document_id); PatientReleasePolicy(document_version_id) **Role:** portal_patient, portal_support
- **API:** GET portal/me/own-records/released-results/appointments; POST own-request/cancel/correction
- **กติกา:** patient_id มาจาก session/link ที่เจ้าหน้าที่รับรอง ไม่เชื่อ request parameter; อ่านเฉพาะของตนและข้อมูลที่ release แล้ว
- **Acceptance:** portal user A เห็นผลของ A และขอนัดได้; เปลี่ยน URL/id เป็นผู้ป่วย B ต้อง 403/404 โดยไม่เปิดข้อมูล
- **เชื่อม:** D34 local sessions, D01 verified identity, D02 booking และ D10/D11 released results
- **ภายนอก:** eID/SMS/email; development login และ in-app requests ทำงานได้ก่อนเชื่อม

### D22 เวชระเบียน เอกสาร และการลงนาม

เดิม **planned** → เป้าหมาย **L2**; L3: J01, J02, J05, J08

- **หน้า:** document list/เวอร์ชัน/ไฟล์แนบ; document timeline และผู้ลงนาม; ร่าง/ตรวจ/attest/สร้าง amendment
- **Workflow:** เอกสารที่มีฉบับและการรับรองโดยคน; สถานะ draft, in_review, attested, returned, amended
- **Entity/FK:** Document(patient_id,encounter_id); DocumentVersion(document_id,content_hash); DocumentAttestation(version_id,user_id); DocumentAmendment(original_version_id,new_version_id) **Role:** clinical_author, reviewer, medical_records
- **API:** GET documents/versions/attachments; POST draft/review/return/attest/amend
- **กติกา:** ฉบับรับรองห้าม overwrite; actor/version/hash binding; attestation ภายในไม่อ้าง qualified digital signature
- **Acceptance:** รับรอง v1 แล้วแก้ไขต้องเกิด amendment/v2; อ่าน hash/ผู้รับรอง/เหตุผลย้อนหลังได้ครบ
- **เชื่อม:** D03/D06/D10/D11 documents, D20 referral packet และ D37 evidence
- **ภายนอก:** PKI/signing/document repositories; local authenticated attestation ไม่รอ certificate service

### D23 ค่าบริการ ราคา และสิทธิการรักษา

เดิม **integration-planned** → เป้าหมาย **L2**; L3: J03, J05

- **หน้า:** price/coverage catalog และ open bills; charge breakdown/price snapshot; กำหนดราคามีผล/เพิ่มรายการ/ตรวจและออกบิล
- **Workflow:** ค่าบริการจากราคาฉบับที่ใช้จริง; สถานะ open, priced, reviewed, invoiced, adjusted, cancelled
- **Entity/FK:** PriceListVersion(organization_id,effective_from); PriceItem(catalog_item_id,price_version_id); CoverageRecord(patient_id); Charge(encounter_id,source_record_id,price_snapshot); Invoice(encounter_id); InvoiceAdjustment(invoice_id,original_charge_id,reason,amount,approver_id) **Role:** billing_officer, pricing_admin, coverage_officer
- **API:** GET prices/coverage/charges/bills; POST price-version/charge/reprice-draft/review/invoice/adjust
- **กติกา:** Decimal amount/currency; issued bill ไม่ถูกเปลี่ยนย้อนหลังจากราคาใหม่; source charge/idempotency ป้องกันซ้ำ; adjustment/credit เป็น record ใหม่อ้าง invoice/charge เดิมพร้อมเหตุผล ผู้อนุมัติ และผลต่อ receivable โดยไม่ overwrite posted lines
- **Acceptance:** ออกบิลด้วยราคา v1 แล้วเปิดราคา v2 บิลเก่ายังยอดเดิม; source event ซ้ำไม่เพิ่ม charge; credit/adjustment มี reference และยอดของตน โดยต้นฉบับยังอ่านได้และ retry ไม่ลงซ้ำ
- **เชื่อม:** D07/D08/D10 services → D24 claim หรือ D25 receipt; D26 แยก cost
- **ภายนอก:** Payer eligibility/fee schedules; local synthetic price/coverage catalog ไม่รอ payer

### D24 เคลม ลูกหนี้ และการกระทบยอดเงินชดเชย

เดิม **integration-planned** → เป้าหมาย **L2**; L3: J05

- **หน้า:** claim draft/validation/remittance worklist; claim lines และ adjudication history; ร่าง/ตรวจ/ส่งออก/นำเข้า synthetic remittance
- **Workflow:** เคลมท้องถิ่นและการพิจารณาจำลอง; สถานะ draft, validated, exported, simulated_submitted, adjudicated, reconciliation_reviewed
- **Entity/FK:** Claim(invoice_id,patient_id,encounter_id); ClaimLine(charge_id); ClaimSubmission(claim_id,mode,external_ack_id); RemittanceBatch(source,synthetic); Adjudication(claim_line_id,approved_amount,decision) **Role:** claim_officer, claim_reviewer, receivable_officer
- **API:** GET claims/validation/adjudications; POST draft/validate/export/simulate-submit/import-remittance/reconcile
- **กติกา:** billed/submitted/approved/gross_received/refunded/net_received เป็นคนละค่าและหลักฐาน; imported approval ไม่ลง cash received; external acknowledgement ห้ามปลอม
- **Acceptance:** บิล 1000 ส่งเคลมจำลองแล้ว remittance อนุมัติ 800: แสดง billed=1000/approved=800/gross_received=0/refunded=0/net_received=0 จนมี D25 receipt; import ซ้ำไม่เพิ่มยอด
- **เชื่อม:** D23 invoice → D35 local adapter → D25 receivable/receipt; D26 cost แยก
- **ภายนอก:** Real payer formats/rules/ack; local claim draft/export และ synthetic remittance ทำงานได้เอง

### D25 บัญชี การเงิน การรับชำระและคืนเงิน

เดิม **planned** → เป้าหมาย **L2**; L3: J05, J06

- **หน้า:** receivable/payable/cash journal list; invoice allocations/ledger detail; รับเงิน/จ่าย/จัดสรร/ขอคืนและอนุมัติ
- **Workflow:** รับชำระและปรับปรุงด้วยรายการกลับบัญชี; สถานะ draft, reviewed, posted, reversed, refund_requested, refund_approved, refunded
- **Entity/FK:** PaymentReceipt(payer_id,currency); PaymentAllocation(receipt_id,invoice_id,claim_id); LedgerEntry(source_record_id); LedgerLine(entry_id,account_id,debit,credit); Refund(original_receipt_id) **Role:** cashier, accountant, refund_approver
- **API:** GET balances/receipts/ledger; POST receive/allocate/review/post/refund-request/approve/refund/reverse
- **กติกา:** balanced Decimal journal; posted rows immutable; refund/reversal เป็น record แยกอ้างต้นทางและยอดคืนสะสมไม่เกินยอดที่คืนได้; retry ไม่รับหรือคืนเงินซ้ำ; แยก gross_received, refunded และ net_received พร้อม payment allocations
- **Acceptance:** รับ 800 ผูกเคลมเดิม แล้วคืน 100 ผ่านผู้อนุมัติ: gross_received=800, refunded=100, net_received=700 พร้อม journal สมดุลและ refund record อ้าง receipt เดิม; retry ไม่ลงซ้ำ
- **เชื่อม:** D23 invoices, D24 adjudication, D27 payables และ D26 reporting
- **ภายนอก:** Bank/payment gateway/accounting export; local synthetic receipt/ledger ไม่รอเงินจริง

### D26 ต้นทุนบริการ งบประมาณ และการวิเคราะห์ทรัพยากร

เดิม **planned** → เป้าหมาย **L2**; L3: J05, J06

- **หน้า:** cost-center/budget/variance dashboard; ต้นทุนบริการและวิธีจัดสรร; กรอก/นำเข้าต้นทุนภายใน/ตรวจและ post
- **Workflow:** ต้นทุนและงบที่ตรวจที่มาได้; สถานะ draft, reviewed, posted, reversed
- **Entity/FK:** CostCenter(department_id); BudgetVersion(cost_center_id,period); CostEntry(source_movement_id,ledger_line_id,encounter_id); CostAllocation(entry_id,method_version) **Role:** cost_accountant, budget_owner
- **API:** GET budgets/cost-lines/variance; POST budget-version/cost-entry/allocation/review/post/reverse
- **กติกา:** billed/submitted/approved/gross_received/refunded/net_received/outstanding/cost แยกคอลัมน์; allocation มีวิธี/รุ่น; ไม่ตีความยอดอนุมัติเป็นเงินรับหรือกำไร
- **Acceptance:** ใช้วัสดุต้นทุน 200 และค่าแรงที่กรอก 100: cost=300 แยกจาก billed=1000, approved=800, gross_received=800, refunded=100 และ net_received=700 พร้อม source links; outstanding อิง receivable allocations/adjustments ที่กำหนด ไม่อนุมานจาก refund เพียงค่าเดียว
- **เชื่อม:** D28 stock cost, D25 ledger, D23 billing และ D24 remittance
- **ภายนอก:** Payroll/ERP/costing policy; local recorded costs และ versioned allocation เริ่มได้

### D27 จัดซื้อ สัญญา รับพัสดุ และเจ้าหนี้

เดิม **planned** → เป้าหมาย **L2**; L3: J06

- **หน้า:** purchase request/PO/receipt list; supplier/contract/PO detail; ขอซื้อ/อนุมัติ/รับของ/ตรวจ invoice
- **Workflow:** ซื้อและรับเข้าคลัง; สถานะ draft, approved, po_recorded, part_received, received, invoice_verified, closed
- **Entity/FK:** Supplier(organization_id); PurchaseRequest(department_id); PurchaseOrder(supplier_id,contract_id); GoodsReceipt(po_id); SupplierInvoice(receipt_id) **Role:** requester, procurement_officer, purchase_approver, receiving_officer
- **API:** GET suppliers/requests/orders/receipts; POST request/approve/po/receive/verify-invoice/close
- **กติกา:** quantity/price snapshot; รับซ้ำตาม receipt key ไม่ได้; inventory receipt และ payable ผูกกันโดยไม่สร้างเงินจริงหรือส่ง PO ภายนอกเอง; การแก้ receipt ที่ post แล้วใช้ correction/return record อ้างต้นทางและกติกาปริมาณสะสมของ D28 ไม่เขียนทับจำนวนรับเดิม
- **Acceptance:** รับของบางส่วนแล้วครบ สต็อกเพิ่มตามรับจริงและ AP ตรง invoice; replay receipt ไม่เพิ่มของซ้ำ
- **เชื่อม:** D28 goods movements, D25 payables และ D26 budget/cost center
- **ภายนอก:** Supplier/e-procurement/accounting connectors; PO ท้องถิ่นระบุยังไม่ส่งภายนอก

### D28 คลังยา เวชภัณฑ์ และห่วงโซ่อุปทาน

เดิม **planned** → เป้าหมาย **L2**; L3: J03, J06

- **หน้า:** stock/lot/location/count worklist; movement ledger และ reservations; รับ/จ่าย/โอน/คืน/ตรวจนับปรับยอด
- **Workflow:** เคลื่อนไหว stock แบบ transactional; สถานะ draft, validated, posted, reversed
- **Entity/FK:** InventoryItem(unit_id); InventoryLot(item_id,expiry_date); StockLocation(department_id); StockMovement(lot_id,from_location_id,to_location_id,source_record_id,original_movement_id,disposition); StockReservation(source_task_id) **Role:** storekeeper, stock_approver, pharmacist
- **API:** GET stock/lots/movements/counts; POST receive/reserve/issue/transfer/return/count/approve-adjustment/reverse
- **กติกา:** ledger/ยอดคงเหลือตรงกัน; no negative stock; หน่วย/ต้นทุน/lot ชัดเจน; lock/version ป้องกัน concurrent issue; posted movement immutable; return/reversal สร้างรายการใหม่อ้าง movement เดิม จำกัดยอดสะสมตามจำนวนที่ยังคืน/กลับรายการได้ และตรวจ disposition ก่อนกลับเป็น available
- **Acceptance:** จ่ายของชิ้นสุดท้ายพร้อมกันสำเร็จหนึ่งคำสั่ง; โอนระหว่างคลังแล้วผลรวมคงเดิมและตาม lot ได้; return/reversal ซ้ำหรือเกินยอดเดิมถูกปฏิเสธโดย posted movement เดิมคงอยู่
- **เชื่อม:** D27 receipts, D08 dispense, D18 blood lot และ D26 cost entries
- **ภายนอก:** Warehouse/robot/GS1 external catalog; local lots/locations ทำงานได้เอง

### D29 ครุภัณฑ์และวิศวกรรมการแพทย์

เดิม **planned** → เป้าหมาย **L2**; L3: J09

- **หน้า:** asset register/maintenance calendar; asset history/work order; ลงทะเบียน/นัดซ่อม/ตรวจปล่อยใช้งาน
- **Workflow:** ครุภัณฑ์และ maintenance; สถานะ registered, in_service, maintenance_due, under_maintenance, verified, retired
- **Entity/FK:** EquipmentAsset(department_id,location_id); MaintenancePlan(asset_id); MaintenanceWorkOrder(asset_id,technician_id); ReleaseVerification(work_order_id,verifier_id) **Role:** biomedical_engineer, technician, asset_custodian
- **API:** GET assets/maintenance/history; POST asset/schedule/start/record/verify/release/retire
- **กติกา:** งานซ่อมยังไม่ verify ห้ามกลับ in_service; user มีสิทธิ์ปล่อย; ไม่ควบคุมเครื่องมือแพทย์จริง
- **Acceptance:** เปิดซ่อมเครื่องสังเคราะห์แล้วห้องตรวจเห็น unavailable; ผู้ตรวจปล่อยแล้วจึงจองใช้งานได้
- **เชื่อม:** D11/D12 resource scheduling, D27 procurement และ D26 depreciation/cost inputs
- **ภายนอก:** Vendor telemetry/CMMS/calibration services; local maintenance evidence ไม่รออุปกรณ์

### D30 บุคลากร ตารางเวร และสมรรถนะ

เดิม **planned** → เป้าหมาย **L2**; L3: J07, J09

- **หน้า:** staff/credential list/roster calendar; staff privileges และ roster version; สร้างเวร/ตรวจชน/เผยแพร่/รับทราบ
- **Workflow:** ตารางเวรและ credential ที่มีผู้ตรวจ; สถานะ draft, reviewed, published, acknowledged, revised
- **Entity/FK:** StaffMember(user_id,department_id); Credential(staff_id,status,valid_until); RosterVersion(department_id); RosterShift(roster_version_id,staff_id); PrivilegeGrant(staff_id,permission_id) **Role:** hr_officer, roster_manager, credential_reviewer, staff
- **API:** GET staff/credentials/rosters; POST staff/credential-review/roster/validate/publish/acknowledge/revise
- **กติกา:** ไม่ลงเวรชนเวลาตามกติกาที่ตั้ง; published roster มี version; credential ระงับต้องมีผลต่อ privilege ที่ผูกไว้
- **Acceptance:** เผยแพร่เวรและพนักงานรับทราบ; ระงับ credential แล้วคำสั่งที่ต้องใช้ privilege นั้นถูกปฏิเสธและ audit
- **เชื่อม:** D34 identity/permissions, D06 handover, D02/D12 practitioner schedule
- **ภายนอก:** HR/payroll/licensing registries; local staff/roster/manual credential verification เริ่มได้

### D31 CSSD ซักฟอก อาคาร และบริการสนับสนุน

เดิม **planned** → เป้าหมาย **L2**; L3: J09

- **หน้า:** CSSD cycle/linen dispatch/facility work-order lists; เครื่องมือ/ผ้า/พื้นที่และประวัติ; ฟอร์ม cycle, ส่งผ้า, งานซ่อมแยกกัน
- **Workflow:** CSSD release พร้อมหลักฐาน; ผ้าและงานอาคารใช้ state คนละชุด; สถานะ received, cleaned, cycle_recorded, quarantined, release_reviewed, released
- **Entity/FK:** InstrumentSet(asset_id); SterilizationCycle(set_id,operator_id); CycleRelease(cycle_id,reviewer_id); LinenDispatch(ward_id); FacilityWorkOrder(location_id,assignee_id) **Role:** cssd_operator, cssd_release_reviewer, linen_staff, facility_technician
- **API:** GET cycles/sets/linen/work-orders; POST cycle/evidence/quarantine/release; POST linen-issue/return; POST facility-assign/verify-close
- **กติกา:** ไม่ตัดสิน sterility อัตโนมัติ; release โดยคนมีหลักฐาน; linen issued→returned→reconciled และ facility opened→assigned→verified→closed ต้องแยก state
- **Acceptance:** cycle ที่ถูก quarantine ห้ามส่งชุดให้ห้องผ่าตัด; ชุด released ตามกลับ cycle ได้ และการคืนผ้าไม่เปลี่ยนสถานะเครื่องมือ
- **เชื่อม:** D12 instrument demand, D05 linen/ward และ D29 asset/location
- **ภายนอก:** Sterilizer/laundry/facility systems; manual recorded evidence และงานท้องถิ่นไม่รอ connector

### D32 คุณภาพ ความเสี่ยง และการควบคุมการติดเชื้อ

เดิม **planned** → เป้าหมาย **L2**; L3: J09

- **หน้า:** incident/CAPA/surveillance worklist; investigation และ action evidence; รายงาน/ประเมิน/มอบหมาย/ตรวจประสิทธิผล
- **Workflow:** เหตุการณ์และการปิด corrective action; สถานะ reported, triaged, investigating, action_planned, effectiveness_review, closed
- **Entity/FK:** Incident(organization_id,encounter_id_optional,reporter_id); RiskReview(incident_id); CAPA(incident_id,owner_id); EffectivenessCheck(capa_id,reviewer_id); SurveillanceCase(case_definition_version_id) **Role:** quality_officer, risk_reviewer, infection_control_officer
- **API:** GET incidents/capa/restricted-detail; POST report/triage/investigate/assign/evidence/review/close
- **กติกา:** reporter identity จำกัดสิทธิ์; classification/ติดเชื้อยืนยันด้วยคน; ปิด CAPA ต้องมีผู้ตรวจและ evidence
- **Acceptance:** รายงานเหตุแล้วส่ง CAPA ผู้รับผิดชอบแนบหลักฐาน ผู้ตรวจปิด; ผู้ไม่มีสิทธิ์อ่านชื่อผู้รายงานไม่ได้
- **เชื่อม:** D03/D05 encounter reference, D22 evidence และ D33 aggregate reports
- **ภายนอก:** Incident/public-health systems และ case definitions; local workflow ไม่รอหน่วยภายนอก

### D33 รายงานสาธารณสุขและข้อมูลระดับเครือข่าย

เดิม **planned** → เป้าหมาย **L2**; L3: J09

- **หน้า:** report definitions/period/submission list; source lineage และ quality errors; สร้างชุดรายงาน/ตรวจ/ส่งออก/ออกฉบับแก้
- **Workflow:** รายงานจากข้อมูลจริงในแอป; สถานะ draft, generated, reviewed, exported, corrected
- **Entity/FK:** ReportDefinition(version,field_mapping); ReportingPeriod(organization_id); ReportBatch(definition_id,period_id); ReportLineage(batch_id,source_record_id); SubmissionEvidence(batch_id,source_type) **Role:** reporting_officer, report_reviewer
- **API:** GET reports/definitions/lineage/errors; POST generate/review/export/correction/record-ack
- **กติกา:** missing≠zero; นิยามและ sourceversion ต้องตามได้; exported ไม่แปลว่าหน่วยรับยอมรับ; ไม่อ้างมาตรฐานไทยที่ยังไม่ตรวจ
- **Acceptance:** สร้างรายงานยอดจาก encounters แล้วตามทุกรายการกลับต้นทางได้; correction สร้าง batch ใหม่ไม่เขียนทับที่ export แล้ว
- **เชื่อม:** D10/D32 source data, D36 cohorts และ D35 external acknowledgement
- **ภายนอก:** Public-health/network submission formats; local defined export ทำได้ก่อนเชื่อม

### D34 ตัวตนผู้ใช้งาน สิทธิ และการตรวจสอบการเข้าถึง

เดิม **planned** → เป้าหมาย **L2**; L3: J01, J07, J10

- **หน้า:** login/logout/current-user; user/role/scope/session administration; สร้างบัญชี/ให้สิทธิ์/ปิดบัญชี/ถอน session
- **Workflow:** local development account/session lifecycle; สถานะ created, active, suspended, disabled
- **Entity/FK:** UserIdentity(organization_id,password_hash); Role; Permission; UserRole(user_id,role_id,department_scope); UserPatientScope(user_id,patient_id); Session(user_id,expires_at,revoked_at) **Role:** identity_admin, all_authenticated_roles
- **API:** POST auth/login/logout/revoke; GET auth/me/users/roles/sessions; POST user/role-grant/suspend; server authorization ทุก write/read
- **กติกา:** session จริงไม่ใช่ public demo token; password hash/secure cookie/CSRF ตามวิธี auth; scope enforcement ฝั่ง server; session state active→revoked/expired แยกบัญชี
- **Acceptance:** login ถูก/ผิด,logout,หมดอายุและถอนสิทธิ์ต้องมีผลจริง; ผู้ใช้ต่าง patient/organization อ่านหรือเขียนข้าม scope ไม่ได้
- **เชื่อม:** ทุก domain ใช้ actor/scope เดียวกัน; D21 ผูก portaluser กับ patient; D30 ผูก staff privileges
- **ภายนอก:** Production IdP/OIDC/SSO/MFA; local development authentication ไม่ต้องรอ auth server ภายนอก

### D35 การเชื่อมต่อระบบ คำศัพท์ และคุณภาพการแลกเปลี่ยน

เดิม **integration-planned** → เป้าหมาย **L2**; L3: J05, J08

- **หน้า:** inbox/outbox/adapter monitor; message validation/retries/ack trace; ตั้ง localstub/รับข้อความ/ตรวจ/ส่งต่อ/กระทบยอด
- **Workflow:** ข้อความและ local adapter ที่มีผลตรวจจริง; สถานะ received, validated, rejected, queued, delivered_local, failed, acknowledged_local
- **Entity/FK:** IntegrationMessage(organization_id,contract_version,source_id); InboxReceipt(message_id,idempotency_key); OutboxEvent(source_record_id,message_id); DeliveryAttempt(message_id,adapter_id); ReconciliationTask(message_id) **Role:** integration_operator, integration_admin
- **API:** GET inbox/outbox/errors/attempts; POST validate/accept/enqueue/local-deliver/retry/reconcile
- **กติกา:** duplicate/out-of-order ตรวจจริง; local/simulated ack แยก external verified; ไม่เปลี่ยนเป็น sent/received ภายนอกเมื่อไม่มี endpoint
- **Acceptance:** ส่ง synthetic message ซ้ำสองครั้งเกิด domain transaction ครั้งเดียว; schema ผิดเข้าคิว error และ retry เก็บ attempt เดิมครบ
- **เชื่อม:** D10 result messages, D20 referrals, D24 syntheticremittance และ D33 exports
- **ภายนอก:** FHIR/HL7/DICOM/payer adapters; แยก protocol และเปิด L4 ทีละ connector หลัง verify

### D36 คลังวิเคราะห์ ข้อมูลวิจัย และการใช้ข้อมูลรอง

เดิม **planned** → เป้าหมาย **L2**; L3: L2/shared-context acceptance

- **หน้า:** dataset/cohort catalog; preview/lineage/version/split summary; กำหนด cohort แบบ allowlist/อนุมัติ/freeze/export
- **Workflow:** dataset snapshot ที่ทำซ้ำได้; สถานะ draft, previewed, approved, frozen, exported, revoked
- **Entity/FK:** CohortDefinition(version,allowed_filters); DatasetVersion(cohort_id,source_snapshot_id); DatasetRowLineage(dataset_id,source_record_id); DatasetAccess(user_id,dataset_id); DatasetSplit(patient_id,partition) **Role:** data_steward, authorized_analyst, dataset_reviewer
- **API:** GET datasets/preview/lineage/access; POST cohort/approve/freeze/export/revoke
- **กติกา:** ไม่รัน SQL อิสระจาก LLM; scope และ export permissions; patient ไม่ข้าม train/test; revoked ไม่อ้างว่าเรียกคืนไฟล์ที่ download ไปแล้ว
- **Acceptance:** freeze cohort แล้วเปลี่ยน source ข้อมูล snapshot เดิมยังทำซ้ำได้; split ไม่มี patient ซ้ำข้ามชุดและ unauthorized export ถูกปฏิเสธ
- **เชื่อม:** D01/D03/D10 sources, D33 reporting และ D37 evaluation inputs
- **ภายนอก:** Research warehouse/external cohorts; ใช้ syntheticPGsnapshot ภายในก่อน

### D37 AI และระบบช่วยตัดสินใจ

เดิม **planned** → เป้าหมาย **L2**; L3: J01, J08

- **หน้า:** AI workbench/run/evaluation list; evidence/proposal/review/version history; เลือกงาน/สร้าง proposal/แก้/อนุมัติ/commit
- **Workflow:** ข้อเสนอ AI ที่มี human review และ policy; สถานะ pending, approved, rejected, committed
- **Entity/FK:** AIUseCase; ModelRegistration(provider_id,artifact_revision); InferenceRun(task_id,outcome); Proposal(task_id,evidence_snapshot_id,version,action_hash); HumanReview(proposal_id,user_id); EvaluationRun(dataset_version_id) **Role:** authorized_requester, reviewer, ai_operator
- **API:** GET tasks/runs/evidence/proposals/models; POST propose/edit/review/commit; GET policy/capability/evaluation status
- **กติกา:** แก้ไขสร้าง version ใหม่ใน pending ไม่ใช้ approval เดิม; approval ผูก version/hash/evidence; fail/timeout/abstain อยู่ denominator; explicit mock และ no live fallback; ไม่มี autonomous clinical write
- **Acceptance:** แก้ proposal แล้ว approval เดิมใช้ไม่ได้; retry commit ไม่ซ้ำ; failed attempt ไม่มี proposal สำเร็จแอบแทรกและตรวจ reason ได้
- **เชื่อม:** D22 documentevidence, D07 scopedtasks, D34permissions และ D36evaluationdataset
- **ภายนอก:** Qwen/Typhoon/MedGemma/cloud endpoints; exactrevision/capabilities ต้อง verify ก่อน L4 แต่ mockL2 ทำต่อได้

### D38 การเดินระบบ ความต่อเนื่อง และการกู้คืน

เดิม **planned** → เป้าหมาย **L2**; L3: J09

- **หน้า:** health/readiness/jobs/migration/backup dashboard; run logs/checksums/restore verification; สั่ง localbackup/restore-to-isolated-target/ตรวจผล
- **Workflow:** backup และ restore ที่รันจริง; สถานะ requested, running, completed, failed, restore_started, restore_verified, restore_failed
- **Entity/FK:** SchemaMigration(version,checksum); OperationalJob(actor_id,command_kind); BackupArtifact(storage_object_id,sha256,db_version); RestoreRun(backup_id,isolated_target,verification_result); ServiceHealthCheck(component,observed_at) **Role:** operations_admin, backup_operator, read_only_auditor
- **API:** GET health/ready/jobs/migrations/backups; POST local-backup/isolated-restore/verify via allowlisted job runner; CLI migration จริง
- **กติกา:** ห้ามปุ่ม success ปลอม; command allowlist และ admin permission; restore เฉพาะ isolated DB ไม่ทับฐานใช้งาน; ครอบคลุม DB+files+manifest
- **Acceptance:** สร้าง backup จาก PostgreSQL จริงแล้ว restore ลงฐานทดสอบแยก ตรวจ row counts/FKs/hashes/เอกสารและ audit ผ่านก่อนแสดง verified
- **เชื่อม:** D34 admin/audit; ตรวจข้อมูล D01/D22/D24/D25/D28/D35 หลัง restore
- **ภายนอก:** Productionstorage/monitoring/KMS/HA; localpgbackup/restore/readiness ไม่ต้องรอ cloud

## Journeys สำหรับความต่อเนื่อง L3

- **J01 Login registration → ลงทะเบียน → นัด/คิว → เปิด OPD → clinician เปิด encounter → document → AI proposal/edit/review → result** — D34, D01, D02, D03, D22, D37. patient/encounter/document version เดียวกัน; role change และ audit ถูกต้อง
- **J02 Clinician สร้าง lab order → lab รับงาน/เก็บ specimen → ลงผลสังเคราะห์ → release → clinician acknowledge** — D03, D07, D10, D22. order/result linkage และ correction history; ไม่มีการอ้างว่า LIS เชื่อมแล้ว
- **J03 Medication order → pharmacist review → จ่ายตาม lot → stock movement → charge** — D03, D07, D08, D28, D23. transaction, lot/expiry/status checks, quantity conservation และไม่จ่าย/คิดเงินซ้ำเมื่อ retry
- **J04 Admit → จัดเตียง → transfer → nursing/handoff → discharge → follow-up** — D01, D04, D05, D06, D02, D20. ไม่มีเตียงซ้อน, current location/version ตรงกัน, tasks ผูก encounter ถูกต้อง
- **J05 Charges → invoice/claim draft → completeness review → synthetic remittance → receipt/refund/reconciliation → cost view** — D23, D24, D25, D26, D22, D35. billed/submitted/approved/gross_received/refunded/net_received/outstanding/cost แยกกัน; ไม่มีการอ้างส่ง payer/รับเงินจริง
- **J06 Purchase request → approval → PO → goods receipt → lot/stock → issue/return → supplier obligation** — D27, D28, D25, D26. trace documents, quantities, duplicate receipt/issue prevention และ authorized posting
- **J07 User/role administration → login/scope change → prohibited API call → revoked session → audit** — D30, D34, D01. อ่าน/เขียน/ส่งออกข้ามสิทธิไม่ได้; audit metadata ไม่เปิด secret/body เกินจำเป็น
- **J08 Imaging request → synthetic file/study → local report/DR task → human review → referral document** — D03, D07, D11, D37, D22, D20, D35. file checksum และ patient/encounter linkage; ไม่มีผล DR/CAD ที่แต่งขึ้นเป็น live prediction
- **J09 Facility/admin tasks → maintenance/quality incident → corrective action → support workflow → operational report** — D29, D30, D31, D32, D33, D38. shared staff/asset/facility references และผลสรุปจาก records จริง
- **J10 Login patient portal → ดู encounter/result ที่เผยแพร่ให้ตน → ส่ง appointment/follow-up request** — D21, D34, D01, D02, D10, D11, D20. patient user เห็นเฉพาะ subject ที่ได้รับอนุญาต; staff รับคำขอผ่าน worklist เดียวกัน

## วิธีส่งต่อ Work/Codex

ใช้ DOMAIN_IMPLEMENTATION_MATRIX.json เป็น machine-readable checklist: ทำ implementation tracker แยกเพื่อบันทึก owner, UI/API/service/migration/tests และผลคำสั่งจริงต่อ ID อัปเดต actual status จากหลักฐาน ไม่เปลี่ยน target เป็น PASS เพราะมีหน้าจอหรือ schema

พัฒนาเป็นกลุ่มในระบบเดียวได้ แต่ minimum full-system development release ต้องครบ 38 domains ที่ L2 และ J01–J10 ที่ L3; งานค้างแสดง INCOMPLETE/NOT_RUN เก็บ L4 ราย connector แยกกันเพื่อไม่ให้การไม่มี endpoint หยุด workflow ภายในทั้งหมด
