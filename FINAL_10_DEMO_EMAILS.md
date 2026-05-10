# WalkPA Final 10 Fresh Demo Emails

Send these 10 fresh emails to the Gmail account connected to WalkPA before recording the final walkthrough.

Use another Gmail account if possible so they appear as real incoming emails. Send them in this order, with Email 10 sent last, so all 10 appear at the top of the inbox.

---

## Email 1: urgent decision requiring user input

Subject:

```text
Urgent: need your decision by EOD
```

Body:

```text
Hey Tejas,

Sorry for the rush, but I need your decision by end of day so we can move forward.

Can you please confirm whether you are okay with the latest version?

Thanks,
Rohan
```

Expected WalkPA behaviour:

```text
Category: needs_user_input
Action: label WalkPA/Needs Your Input
Follow-up: user says yes/no, then WalkPA drafts or sends approved reply
```

---

## Email 2: sensitive contract requiring approval

Subject:

```text
Contract review before we confirm
```

Body:

```text
Hey Tejas,

Can you review the contract terms before we confirm this over email? There are a few legal points that might need careful wording.

Thanks,
Maya
```

Expected WalkPA behaviour:

```text
Category: needs_user_input
Action: label WalkPA/Needs Your Input
Follow-up: user gives wording, then WalkPA drafts or sends approved reply
```

---

## Email 3: meeting request

Subject:

```text
Can we move our project call?
```

Body:

```text
Hey Tejas,

Can we reschedule our project call for tomorrow? I am free in the afternoon, but happy to work around your calendar.

Could you send me a couple of times that work for you?

Thanks,
Alex
```

Expected WalkPA behaviour:

```text
Category: needs_meeting
Action: create Gmail draft + create Calendar hold + Google Meet link
```

---

## Email 4: onboarding calendar request

Subject:

```text
Find a time for the onboarding call
```

Body:

```text
Hey Tejas,

Can you find a time for an onboarding call next week? A 30-minute slot would be perfect.

Thanks,
Priya
```

Expected WalkPA behaviour:

```text
Category: needs_meeting
Action: create Gmail draft + create Calendar hold + Google Meet link
```

---

## Email 5: normal reply needed

Subject:

```text
Quick follow-up on the proposal
```

Body:

```text
Hey Tejas,

Just following up on the proposal from last week. Could you let me know if you have had a chance to look at it?

No rush, just wanted to check where things are at.

Thanks,
Sarah
```

Expected WalkPA behaviour:

```text
Category: needs_reply
Action: create Gmail draft
```

---

## Email 6: finance routing

Subject:

```text
Invoice for April services
```

Body:

```text
Hi Tejas,

Please find the invoice details for April services. Could you route this to whoever handles finance/admin?

Thanks,
Billing Team
```

Expected WalkPA behaviour:

```text
Category: needs_routing
Action: label WalkPA/Routed-Finance
```

---

## Email 7: operations routing

Subject:

```text
Please pass this to the ops team
```

Body:

```text
Hi Tejas,

Could you pass this to the operations team? It is about room setup and equipment for next week.

Thanks,
Nina
```

Expected WalkPA behaviour:

```text
Category: needs_routing
Action: label WalkPA/Routed
```

---

## Email 8: FYI only

Subject:

```text
FYI: notes from yesterday
```

Body:

```text
Hey Tejas,

Just sending across notes from yesterday. Nothing needed from you right now, just keeping you in the loop.

Thanks,
Jamie
```

Expected WalkPA behaviour:

```text
Category: fyi
Action: no risky action
```

---

## Email 9: low-priority promo

Subject:

```text
50% off lunch today only
```

Body:

```text
Today only: get 50% off selected meals. Use code LUNCH50.

Unsubscribe anytime.
```

Expected WalkPA behaviour:

```text
Category: low_priority
Action: label WalkPA/Low Priority
```

---

## Email 10: event announcement, not a meeting request

Subject:

```text
Join us for a product demo night
```

Body:

```text
You are invited to our next community event. Register now to attend the product demo night.

This is an announcement only.
```

Expected WalkPA behaviour:

```text
Category: low_priority
Action: label WalkPA/Low Priority
```

---

# Final first-pass command

Use this in the demo:

```text
I'm walking to work. Clear my inbox, draft replies, route admin or low-priority messages, schedule meetings, and tell me what you need from me.
```

# Final follow-up command

Use this in the demo:

```text
Tell Rohan yes, I am okay with the latest version. For the contract, say I will review it this afternoon but I do not want to confirm anything yet.
```
