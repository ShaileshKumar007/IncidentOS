# Live Demonstration & Presentation Guide

## Project: IncidentOS
**Document**: Hackathon Demo Script & Verification Guide  
**Status**: Initial Architecture / Approved for Initialization  

---

## 1. Demo Narrative: "Black Friday Checkout Spike"

### The Scenario
It is 2:00 PM during a major promotional sale. The fictional e-commerce checkout service (`checkout-service`) has just been deployed with commit `6014328` ("feat: simplify customer session validation in checkout"). 

Suddenly, unauthenticated guest users attempting to purchase items start receiving `HTTP 500 Internal Server Error`. The conversion rate plummets. 

An alert fires into the engineering Mattermost channel `#incidents`. Rather than scrambling across dashboards, the on-call engineer collaborates with **IncidentOS**.

---

## 2. Live Demo Script (Step-by-Step)

```
Time: 0:00 - 0:30 | Act 1: The Alert & Incident Declaration
Time: 0:30 - 1:15 | Act 2: Multi-Agent Investigation in Switch
Time: 1:15 - 1:45 | Act 3: Remediation & Empirical QA Testing
Time: 1:45 - 2:15 | Act 4: The Human Approval Gate in Mattermost
Time: 2:15 - 2:45 | Act 5: Autonomous Postmortem & Audit Record
```

### Act 1: The Alert & Incident Declaration (Mattermost)
1. **Action**: The alert is posted to Mattermost `#incidents`:
   ```
   [ALERT] CheckoutServiceErrorRateSpike: 15% of checkout requests returning HTTP 500 on /api/checkout.
   ```
2. **What to show**:
   - The **Incident Commander** automatically ingests the alert.
   - It posts an immediate acknowledgment:
     > **[Incident Declared] SEV-1**: Checkout Service Outage  
     > **Lead**: Incident Commander  
     > **Strategy**: Investigating recent deployment and application logs. Coordinating specialized agents via Switch.
   - Commander creates the investigation plan and delegates tasks.

### Act 2: Multi-Agent Collaboration in Switch
1. **Action**: Switch view to the **Switch Incident Room** (`incident-ops-bridge`).
2. **What to show**:
   - Commander messages the room: assigns log triage to `@log-investigator` and code review to `@code-investigator`.
   - **Log Investigator** queries backend tools:
     > 🔍 **Log Evidence Found**: `java.lang.NullPointerException` at `com.example.checkout.service.PaymentValidator.validate(PaymentValidator.java:42)`. Error rate: 48 occurrences in last 5 minutes.
   - **Code Investigator** queries Git tools:
     > 🔍 **Commit Regression Found**: Commit `6014328` by `ci-bot@fictional-store.internal` removed the `if (customer == null)` guard before invoking `customer.getId()`.
   - Commander synthesizes the findings:
     > 💡 **Root Cause Confirmed**: Guest checkout payloads provide a null customer session. `PaymentValidator.validate()` throws NPE when attempting to read the customer ID.

### Act 3: Remediation & Empirical QA Testing
1. **Action**: Watch Code Investigator and QA Agent in Switch:
   - **Code Investigator**:
     - Prepares isolated fix branch `remediation/issue-checkout-npe`.
     - Adds null check with fallback for guest session IDs.
     - Submits patch diff to Switch.
   - **QA & Validation Agent**:
     - Picks up the branch and triggers backend test runner.
     - Runs JUnit regression test suite.
     - Reports actual execution logs:
       > ✅ **Test Suite Passed**: 5/5 tests passed (including `testGuestCheckout_ShouldSucceed`) in 3.12s. Zero regressions.

### Act 4: The Human Approval Gate (Mattermost)
1. **Action**: Switch back to Mattermost `#incidents`.
2. **What to show**:
   - Incident Commander posts an interactive decision card:
     ```markdown
     ### 🚨 Remediation Proposed for INC-20261104-01
     **Root Cause**: NPE in PaymentValidator.java:42 due to missing guest customer null-check.
     **Regression Commit**: `6014328`
     **Proposed Diff**:
     ```diff
     - UUID customerId = customer.getId();
     + UUID customerId = (customer != null) ? customer.getId() : null;
     ```
     **QA Validation**: 5/5 Tests PASSED (Execution time: 3.12s)
     ```
   - Shows two buttons: **[Approve Remediation]** and **[Reject]**.
3. **The Human Action**:
   - The presenter (human engineer) clicks **[Approve Remediation]**.
   - System displays: `Approved by @alex at 14:03:15 UTC. Approval Token: appr_tok_991823120abc`.

### Act 5: Postmortem Generation & Incident Closure
1. **Action**: Watch Documentation Agent activate in Mattermost:
   - Notice that the **Documentation Agent** was completely dormant until the moment of human approval.
   - The Documentation Agent compiles the exact timeline, citations, diff, test proofs, and human sign-off into a beautiful Markdown Postmortem directly into the channel.
   - Shows status flags:
     - `Approved: YES (@alex)`
     - `Tested: YES (5/5 JUnit tests pass)`
     - `Merged: NO (Awaiting standard PR pipeline)`
     - `Deployed: NO (Manual deployment gate required)`

---

## 3. Fallback & Troubleshooting Procedures

| Risk / Issue | Detection | Fallback Procedure |
| :--- | :--- | :--- |
| Mattermost webhook latency | Interactive button does not render | Use slash command `/incident approve INC-20261104-01` in the chat. |
| Test suite execution slow | Gradle daemon cold start | Warm up the Gradle/Maven daemon before presentation start (`./gradlew --daemon status`). |
| Network disruption | Switch connection reset | IncidentOS local backend maintains local state cache; agents reconnect seamlessly. |
