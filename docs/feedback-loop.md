# Paytm Pulse — Phase 13 Feedback Loop & Continuous Learning

## 1. Overview & Architecture

Paytm Pulse is designed with a full closed-loop learning architecture. The system connects every AI recommendation to merchant decisions, action executions, measured business outcomes, and feedback signals:

```text
Business Event
      ↓
AI Recommendation
      ↓
Merchant Decision (Approval / Rejection)
      ↓
Action Execution (Success / Failure)
      ↓
Closed-Loop Measurement (Baseline vs Observed)
      ↓
Feedback Ingestion & Lineage Tracking
      ↓
Decision Quality & Offline Dataset Export
```

### Complete 6-Stage Lineage Traceability
Every signal strictly tracks lineage back to its root cause:
$$\text{event\_id} \longrightarrow \text{recommendation\_id} \longrightarrow \text{action\_id} \longrightarrow \text{execution\_id} \longrightarrow \text{outcome\_id} \longrightarrow \text{feedback\_id}$$

---

## 2. Objective Outcomes vs Subjective Merchant Feedback

Paytm Pulse strictly distinguishes between:
1. **Objective Measured Business Outcomes**:
   - `POSITIVE`: Proven revenue gain, stockout averted, or customer recovered.
   - `NEUTRAL`: Business continued without significant variance ($\Delta < 2\%$).
   - `NEGATIVE`: Metric degradation or negative return.
   - `INSUFFICIENT_DATA`: Data sparsity prevents empirical determination.
2. **Subjective Merchant Ratings**:
   - `USEFUL` vs `NOT_USEFUL`
   - Numeric ratings (1-5 stars)
   - Qualitative comments (e.g., *"Helped me handle the evening rush easily"*).

A merchant might rate a recommendation as "USEFUL" because it made sense, even if unseasonal weather dampened the final sales numbers, and vice versa. Separating both data streams prevents skewing algorithmic evaluation.

---

## 3. Feedback Signals & Effectiveness States

### Signal Types (`FeedbackType`)
* `MERCHANT_APPROVED` — Recommendation explicitly approved.
* `MERCHANT_REJECTED` — Recommendation explicitly dismissed.
* `ACTION_EXECUTED` — Underlying action executed successfully.
* `ACTION_FAILED` — Action execution threw an error or timed out.
* `POSITIVE_OUTCOME` — Post-action observation demonstrated positive impact.
* `NEUTRAL_OUTCOME` — Post-action observation showed negligible impact.
* `NEGATIVE_OUTCOME` — Post-action observation indicated negative impact.
* `INSUFFICIENT_DATA` — Inconclusive empirical data.
* `MERCHANT_RATING` — Explicit merchant thumbs up/down or review.
* `EXPIRED` — Recommendation timed out without merchant response.

### Lifecycle Effectiveness States (`RecommendationEffectiveness`)
* `SUCCESSFUL`: Approved $\to$ Executed $\to$ Objective Positive Outcome.
* `PARTIALLY_SUCCESSFUL`: Approved $\to$ Executed $\to$ Objective Neutral Outcome.
* `UNSUCCESSFUL`: Approved $\to$ Executed $\to$ Objective Negative Outcome.
* `NOT_MEASURED`: Approved $\to$ Executed $\to$ Awaiting observation window.
* `EXECUTION_FAILED`: Approved $\to$ Action execution failed.
* `REJECTED`: Merchant declined recommendation.
* `EXPIRED`: Pending timeout exceeded.

---

## 4. Bounded Heuristic Scoring (Safety & Guardrails)

Paytm Pulse follows safety-first ML principles.
- **NO unsafe online weight retraining**: Models are NOT automatically rewritten in production on single data points.
- **Bounded Decision Adjustment**: Historical action-type performance applies a bounded adjustment to the Next Best Action score:
$$\text{adjustment} = \text{clamp}\left(0.10 \times (\text{success\_rate} - 0.50), -0.10, +0.10\right)$$
- **Sample Threshold**: Adjustments require at least $2$ measured historical actions to avoid small-sample volatility.

---

## 5. Offline ML Dataset Generation

The endpoint `GET /api/v1/feedback/dataset` generates training rows linking contextual features to business success:
- Features: Merchant category, baseline revenue, urgency, confidence, action parameters.
- Target: `was_approved`, `was_executed`, `objective_impact`, `revenue_change`, `is_success`.
- Enables supervised fine-tuning and offline policy calibration.

---

## 6. REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/feedback` | `POST` | Ingest operational feedback signal |
| `/api/v1/feedback/merchant-rating` | `POST` | Record subjective merchant rating |
| `/api/v1/feedback/{feedback_id}` | `GET` | Retrieve signal by UUID |
| `/api/v1/feedback/recommendation/{rec_id}` | `GET` | Get all feedback signals for a recommendation |
| `/api/v1/feedback/action/{action_id}` | `GET` | Get all feedback signals for an action |
| `/api/v1/feedback/merchant/{merchant_id}` | `GET` | Paginated merchant feedback signals |
| `/api/v1/feedback/merchant/{merchant_id}/summary` | `GET` | Aggregate acceptance & success rates for merchant |
| `/api/v1/feedback/action-types` | `GET` | System-wide performance by action type |
| `/api/v1/feedback/recommendation/{rec_id}/effectiveness` | `GET` | Evaluated lifecycle effectiveness |
| `/api/v1/feedback/dataset` | `GET` | Offline ML training dataset export |
