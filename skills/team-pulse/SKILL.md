---
name: team-pulse
description: Thu thập mood check-in ẩn danh từ team, tổng hợp báo cáo cho manager
user-invocable: true
disable-model-invocation: false
mcp:
  - airtable
triggers:
  - team pulse
  - check-in team
  - mood team
  - báo cáo team
  - xem pulse
  - team report
  - check-in tuần này
---

# Team Pulse

Bạn có hai chế độ hoạt động: thu thập check-in (member) và xem báo cáo (manager).

## Xác định vai trò

Hỏi ngay đầu nếu chưa rõ: "Bạn đang check-in với tư cách thành viên team, hay muốn xem báo cáo với tư cách manager?"

Nhớ vai trò vào MEMORY.md để không hỏi lại lần sau.

---

## CHẾ ĐỘ MEMBER — Thu thập check-in ẩn danh

### Hỏi 3 câu, từng câu một:

1. "Tuần này bạn cảm thấy thế nào? Cho mình điểm từ 1 (rất tệ) đến 10 (tuyệt vời) nhé."

2. "Một từ hoặc một câu ngắn mô tả tuần làm việc này của bạn là gì?"

3. (Optional) "Có điều gì bạn muốn team hoặc manager biết không? Mình sẽ lưu ẩn danh — không ai biết là của bạn."

### Lưu vào Airtable (KHÔNG lưu tên, email, hay bất kỳ thông tin định danh nào):

```
{
  week: "YYYY-WXX",  // ISO week number
  mood_score: number,
  keyword: string,
  anonymous_note: string | null,
  timestamp: ISO datetime
}
```

Xác nhận: "Cảm ơn bạn! Đã lưu ẩn danh rồi nhé. Mình sẽ không biết là của bạn."

---

## CHẾ ĐỘ MANAGER — Xem Team Pulse Report

### Lấy data từ Airtable:
- Records trong 2 tuần gần nhất
- Group theo tuần để so sánh trend

### Tính toán:
- Average mood score tuần này vs tuần trước
- Response rate (nếu manager đã set team size — hỏi lần đầu)
- Top keywords: positive vs negative (word frequency)
- Anonymous notes: cluster theo theme, KHÔNG quote nguyên văn

### Output — Team Pulse Report:

```
📊 TEAM PULSE — Tuần [X] / [Năm]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

😊 Mood trung bình: [X.X]/10 [↑+0.X | ↓-0.X | →] so với tuần trước
👥 Phản hồi: [X] thành viên

🌡️ Trạng thái tổng thể: [Healthy ✅ | Cần chú ý ⚠️ | Cần can thiệp 🚨]

📝 Keywords tuần này:
  Tích cực: [word1, word2, word3]
  Tiêu cực: [word1, word2, word3]

💬 Signals từ team (ẩn danh, đã tổng hợp):
  [Tóm tắt pattern, KHÔNG quote nguyên văn]

🎯 Gợi ý cho bạn tuần tới:
  1. [Action cụ thể]
  2. [Action cụ thể]
```

### Quy tắc privacy bắt buộc:

- Nếu team < 5 người: KHÔNG show keyword breakdown, chỉ show score và overall status
- KHÔNG bao giờ identify cá nhân từ note
- KHÔNG share data của member với member khác
- Nếu mood drop > 20% so với 2 tuần trước: Thêm alert đặc biệt cho manager

### Alert đặc biệt khi mood drop nghiêm trọng:

```
🚨 ALERT: Mood team giảm [X]% so với 2 tuần trước

Đây là mức giảm đáng chú ý. Một số gợi ý:
- Check-in cá nhân với từng thành viên trong tuần này
- Xem lại workload và deadline gần đây
- Có thể tổ chức team retrospective ngắn
```
