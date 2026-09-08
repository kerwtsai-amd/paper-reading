# Reader-First Paper Reading and Exposition

Read this guide before drafting either an HTML or Confluence paper summary. It defines the explanatory structure shared by both delivery formats; their own templates, evidence syntax, and validators still take precedence for rendering.

## Source and Scope

This guide distills complementary writing patterns from two Zhihu deep-reading articles inspected on 2026-09-08:

- Zhou Yifan's [Attention Is All You Need (Transformer) 论文精读](https://zhuanlan.zhihu.com/p/569527564) defines a beginner reader, supplies only the required machine-translation and RNN background, then deliberately leaves paper order. It teaches attention through a concrete database-query analogy and small calculation before introducing \(Q,K,V\), scaled dot-product attention, self-attention, multi-head attention, and finally the whole architecture.
- zzudongxiang's [论文选读《Congestion Control for Large-Scale RDMA Deployments》](https://zhuanlan.zhihu.com/p/699028060) teaches InfiniBand, RoCEv2, PFC/ECN, and RDMA before introducing DCQCN. It places diagrams beside the concepts they explain, compares adjacent technologies in a table, and proceeds from challenges and shortcomings to design goals and implementation constraints.

Treat both articles as exposition examples, not as technical authorities. The Transformer article has weak source localization and limited critical evaluation; the DCQCN article explicitly says its paper-specific treatment is unfinished. Do not copy their prose, figures, or technical claims without checking the primary paper and any necessary canonical background sources.

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

## Concrete-to-Formal Teaching Pattern

When a mechanism is abstract, do not open with its final equation or architecture diagram. Use this order whenever it improves comprehension:

1. State the concrete task in ordinary language.
2. Walk one small packet, request, token, tensor tile, cache block, or numerical example through the mechanism.
3. Name the state and decisions the reader has already seen.
4. Map those objects to the paper's formal symbols, shapes, and equation.
5. Explain what changes when each important variable grows or shrinks.
6. Rejoin the end-to-end system and state where the simplifying analogy stops being exact.

Each subsection should answer one reader question and, where natural, end by exposing the next unresolved question. This question-driven rhythm is more important than matching the paper's section order.

## Applying the Spine to the Editorial Roles

- **Header thesis:** State the problem, proposed mechanism, and best-supported outcome once. Do not create separate metadata, one-sentence, and Executive Summary chapters that repeat it.
- **`prerequisites`:** Begin with a small prerequisite map or comparison when it materially reduces later cognitive load. Explain only concepts used later and end with a bridge to the paper's exact problem.
- **`problem`:** Organize around `symptom → cause → why the nearest baseline is insufficient → requirements and success criteria`. Keep inputs, outputs, assumptions, and notation attached to that story.
- **`insight`:** Give the smallest example or walkthrough that makes the key mechanism intuitive before expanding it.
- **`method`:** Start with an end-to-end packet, request, tensor, data, or control-flow walkthrough. Then explain components in execution order. Put each equation and method figure next to the design decision it clarifies.
- **`evidence`:** Organize evaluation as claim-test units: `claim → setup and controls → metric → observation → supported conclusion → caveat`. Put result plots inside the unit that interprets them rather than in a gallery.
- **`critique` and `extensions`:** Use limitations, related-work comparisons, independent analysis, reusable ideas, and proposed experiments to test the causal story rather than adding disconnected lists.
- **`reference`:** Keep bibliographic details, glossary, and direct evidence locations for the causal thread here as a low-prominence appendix.

## Background Provenance

Keep source scope explicit:

- **The paper's own background or claim:** cite the paper section, PDF page, and object identifier when applicable.
- **External prerequisite:** use only when the paper does not explain a concept sufficiently for the target reader. Cite a canonical standard, specification, textbook, or first-party technical source, and state that it is external background rather than a claim of the paper. Also cite the paper location that makes the prerequisite relevant when the delivery validator requires a paper-page source.
- **Synthesis:** label the connection between a prerequisite and the paper as `分析`.
- **Hypothesis:** label an untested mechanism or extension as `推測`.

External background cannot repair missing paper evidence. If the paper omits an ablation, deployment detail, or evaluation condition, retain `論文未提供` rather than substituting a blog or related paper.

## Draft Review Gates

Before validation, check all of the following:

- Every prerequisite introduced in `prerequisites` is used later; otherwise remove it.
- Every major method component answers a named problem or requirement.
- Every principal empirical conclusion has a claim-test mapping with conditions and a limitation.
- Paper claims, experimental facts, external background, analysis, and speculation remain distinguishable.
- A reader can reconstruct the end-to-end flow and explain why the method should help before seeing the results.
- Background does not dominate the paper's actual contribution, and the report completes the method, evaluation, and critical analysis even when a style reference did not.
