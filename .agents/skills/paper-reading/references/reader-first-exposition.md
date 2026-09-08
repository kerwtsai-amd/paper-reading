# Reader-First Paper Reading and Exposition

Read this guide before drafting either an HTML or Confluence paper summary. It defines the explanatory structure shared by both delivery formats; their own templates, evidence syntax, and validators still take precedence for rendering.

## Source and Scope

This guide distills the useful writing pattern in zzudongxiang's 2024 Zhihu article [论文选读《Congestion Control for Large-Scale RDMA Deployments》](https://zhuanlan.zhihu.com/p/699028060), inspected on 2026-09-08. The article teaches RDMA prerequisites before introducing DCQCN, places diagrams beside the concepts they explain, compares adjacent technologies, and then proceeds from challenges and shortcomings to design goals and implementation.

Treat the article as a style example, not as a technical authority or a complete paper summary. Its author explicitly says the paper-specific treatment is unfinished. Do not copy its prose, figures, or technical claims into a summary without checking the primary paper and any necessary canonical background sources.

## Reader Model

Write for a technically capable reader who has not read the paper and may lack a small set of domain concepts on which the contribution depends. Before drafting, record internally:

- what the reader probably already knows;
- the minimum prerequisite concepts needed to follow the paper;
- where each prerequisite is used later in the explanation; and
- the central question the reader should be able to answer after each section.

Remove background that is not used to explain a problem, design choice, equation, experiment, or limitation later. A generic tutorial that could be pasted unchanged into many summaries is too broad.

## Explanatory Spine

Build one causal thread through the report:

1. **System context:** Where does the work sit in the larger system or workflow?
2. **Observable problem:** What fails, under which workload or operating condition, and why does it matter?
3. **Root mechanism:** Which queue, signal, dependency, state transition, resource limit, or algorithmic property causes the failure?
4. **Why existing approaches are insufficient:** Compare the closest alternatives by mechanism, assumptions, deployment cost, and failure mode.
5. **Design requirements:** Derive the paper's goals from the preceding constraints rather than presenting a detached feature list.
6. **Proposed mechanism:** First give an end-to-end walkthrough, then explain each component as `input/signal → state or decision → action → intended effect`.
7. **Evidence:** Map each principal claim to the experiment, metric, workload, baseline, result, and caveat that tests it.
8. **Boundary:** State what is not demonstrated, the deployment assumptions, and the remaining questions.

The reader should never have to infer why a prerequisite was introduced, which requirement a component satisfies, or which result supports a conclusion.

## Applying the Spine to the Fixed Sections

- **02 一句話總結:** Include the problem, proposed mechanism, and best-supported outcome. Do not start with broad field background.
- **03 Executive Summary:** Use the compact order `problem → root cause or gap → key insight → mechanism → strongest evidence → boundary`.
- **04 背景與動機:** Begin with a small prerequisite map or comparison when it materially reduces later cognitive load. Explain only the concepts used later and end with a bridge to the exact problem in Section 05.
- **05 問題定義:** Organize around `symptom → cause → why the nearest baseline is insufficient → requirements and success criteria`. Keep formal inputs, outputs, assumptions, and notation attached to that story.
- **06 核心方法:** Start with an end-to-end packet, request, tensor, data, or control-flow walkthrough. Then explain components in execution order and tie every design choice back to a named requirement or failure mechanism.
- **07 公式與理論:** Use equations to clarify decisions, stability, complexity, or scaling behavior. Explain what changes when a variable increases or decreases and where the equation enters the method.
- **08 圖片與圖表導讀:** Place each selected paper figure near the concept or claim it resolves. The reading guide must say what to inspect and why it matters; do not merely restate the caption. Prefer a self-authored structural table over copying a third-party tutorial figure.
- **09–10 實驗設計／實驗結果:** Organize the evaluation as claim-test pairs: `claim → setup and controls → metric → observation → supported conclusion → caveat`. Do not narrate figures only in paper order.
- **11–14:** Use ablations, limitations, related-work comparisons, and independent analysis to test the causal story rather than adding disconnected lists.
- **16 術語表與重點索引:** Include the prerequisites introduced in Section 04 and provide direct evidence locations for the main links in the causal thread.

## Background Provenance

Keep source scope explicit:

- **The paper's own background or claim:** cite the paper section, PDF page, and object identifier when applicable.
- **External prerequisite:** use only when the paper does not explain a concept sufficiently for the target reader. Cite a canonical standard, specification, textbook, or first-party technical source, and state that it is external background rather than a claim of the paper. Also cite the paper location that makes the prerequisite relevant when the delivery validator requires a paper-page source.
- **Synthesis:** label the connection between a prerequisite and the paper as `分析`.
- **Hypothesis:** label an untested mechanism or extension as `推測`.

External background cannot repair missing paper evidence. If the paper omits an ablation, deployment detail, or evaluation condition, retain `論文未提供` rather than substituting a blog or related paper.

## Draft Review Gates

Before validation, check all of the following:

- Every prerequisite introduced in Section 04 is used later; otherwise remove it.
- Every major method component answers a named problem or requirement.
- Every principal empirical conclusion has a claim-test mapping with conditions and a limitation.
- Paper claims, experimental facts, external background, analysis, and speculation remain distinguishable.
- A reader can reconstruct the end-to-end flow and explain why the method should help before seeing the results.
- Background does not dominate the paper's actual contribution, and the report completes the method, evaluation, and critical analysis even when a style reference did not.
