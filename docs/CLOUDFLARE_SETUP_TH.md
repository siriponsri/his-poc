# ตั้ง Cloudflare Tunnel สำหรับ his.ai-cie.com

รอบนี้เตรียมระบบและตัวตรวจไว้แล้ว แต่ยังไม่ได้สร้าง Tunnel, เปลี่ยน DNS หรือเปิดเว็บสาธารณะ โดเมนที่ผู้ใช้เลือกคือ **his.ai-cie.com** ตรวจพบ ai-cie.com ในบัญชี Cloudflare ที่เปิดอยู่ โดยไม่ได้เปลี่ยนค่าบัญชี

ทำข้อ1–5 แล้วกลับมา resume goal ได้เลย ยังไม่ต้องสั่ง route dns หรือ run tunnel ในรอบตั้งค่านี้

## 1. เชื่อมเครื่องกับบัญชี Cloudflare

เปิด PowerShell ในโฟลเดอร์ C:/Users/User/Desktop/myProject/his-poc แล้วรัน:

```powershell
cloudflared tunnel login
```

เบราว์เซอร์จะให้เลือกบัญชีและโดเมน ai-cie.com จากนั้นอนุญาตให้เครื่องจัดการ Tunnel เก็บ cert.pem ไว้ส่วนตัว โปรแกรม cloudflared ติดตั้งอยู่แล้ว

## 2. สร้าง named tunnel

```powershell
cloudflared tunnel create his-poc
```

จด Tunnel UUID และตำแหน่งไฟล์ credentials JSON ที่โปรแกรมแจ้ง ปกติอยู่ใน C:/Users/User/.cloudflared/UUID.json อย่านำไฟล์นี้หรือ cert.pem เข้า Git หรือส่งในแชต หากมีชื่อ his-poc อยู่แล้ว ให้ใช้ Tunnel เดิมที่ตั้งใจใช้ ไม่ต้องลบหรือสร้างทับ

## 3. ตั้ง Cloudflare Access

ใน Cloudflare เปิด Zero Trust แล้วไปที่ Access → Applications → Add an application → Self-hosted ชื่อเมนูอาจต่างเล็กน้อยตามหน้าบัญชี

- ชื่อแอป: HIS POC
- Hostname: his.ai-cie.com
- สร้าง Allow policy เฉพาะอีเมลผู้ทดสอบที่คุณต้องการ
- ให้ policy ครอบคลุมทั้ง hostname รวมถึง /api/v2 โดยไม่ตั้ง Bypass
- จด Team name จากชื่อหน้า xxx.cloudflareaccess.com และ Application Audience (AUD) ของแอปนี้
- ใช้ขอบเขตบริการที่ไม่เสียเงินสำหรับ POC นี้ หากหน้าตั้งค่าขอผูกการชำระเงินหรือยอมรับเงื่อนไขใหม่ ให้หยุดส่วนนั้นและแจ้งตอน resume

Access เป็นประตูชั้นนอก ผู้ใช้ยังต้อง login ด้วยบัญชี HIS และผ่านสิทธิ์/ขอบเขตผู้ป่วยของระบบอีกครั้ง

## 4. ใส่ค่าภายในเครื่อง

```powershell
python scripts/cloudflare_prepare.py init
```

คำสั่งจะเก็บไฟล์เดิมไว้ถ้ามีอยู่แล้ว เปิด var/cloudflare/settings.json แล้วใส่:

```json
{
  "hostname": "his.ai-cie.com",
  "tunnel_id": "ใส่ UUID จากข้อ 2",
  "credentials_file": "C:/Users/User/.cloudflared/UUID.json",
  "access_team_name": "ใส่เฉพาะชื่อทีม ไม่รวม .cloudflareaccess.com",
  "access_audience_tag": "ใส่ AUD ของแอป",
  "origin_port": 8000
}
```

ใช้ / ใน path ตามตัวอย่างเพื่อไม่ต้อง escape ใน JSON ไฟล์นี้อยู่ใน var ที่ Git ไม่เก็บ ค่า hostname ถูกเตรียมไว้แล้ว ส่วนข้อมูลบัญชีที่เหลือต้องมาจากการตั้งจริง

## 5. สร้างและตรวจ profile โดยยังไม่เผยแพร่

```powershell
python scripts/cloudflare_prepare.py prepare
python scripts/cloudflare_prepare.py validate
```

ผลที่ต้องการคือ LOCAL_PROFILE_VALIDATED_NOT_DEPLOYED ตัวตรวจจะเช็ก UUID/credentials, Access, กฎรับ hostname เดียว, cookie แบบ Secure, HTTPS origin และ Compose ที่ไม่เปิดฐานข้อมูล/โมเดลออกภายนอก ค่าที่ยังว่างหรือไม่ตรงจะหยุดพร้อมรหัสสาเหตุ

หลังผ่านแล้ว กลับมาพิมพ์ว่า:

> resume goal: ตั้ง Tunnel และ Access ของ his.ai-cie.com แล้ว prepare/validate ผ่าน

ไม่ต้องส่งรหัสผ่าน token หรือไฟล์ credentials ในแชต

## เมื่อ resume จะทำอะไรต่อ

ตรวจ profile กับแอป build ล่าสุด → ยืนยัน backup → ใช้ HTTPS profile โดยไม่ seed/reset → กำหนด DNS ของ his.ai-cie.com ให้ Tunnel → เปิด connector → ทดสอบจาก URL จริง ทั้ง Access/login/cookie/สิทธิ์ เอกสาร การเรียก Typhoon และ human review/commit/reload ก่อนสรุปว่า deploy ผ่าน

การเผยแพร่จะทำในรอบ resume ตามคำสั่งของเจ้าของ Cloudflare Tunnel ส่งหน้าเว็บและ API ไปแอปเดิมบนเครื่อง ไม่ได้ย้าย PostgreSQL หรือ Typhoon ไป Cloudflare เครื่องนี้ Docker และเส้นทาง dr-train ต้องทำงานอยู่ หากเครื่อง sleep หรือปิด เว็บจะใช้งานไม่ได้

รายละเอียดการเปิด connector, rollback และขอบเขตตรวจ: [CLOUDFLARE_DEPLOYMENT.md](CLOUDFLARE_DEPLOYMENT.md)

แหล่งอ้างอิง: [สร้าง locally managed tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/), [Access self-hosted application](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)
