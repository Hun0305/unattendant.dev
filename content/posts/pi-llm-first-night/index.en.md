---
title: "Eight small LLMs ran overnight on a Pi 4: one 128-token answer took 25 to 53 seconds"
description: "I read the CSV from the first overnight benchmark of eight small LLMs on a Pi 4B (2026-10-26). Generation ran at 2.4 to 5.1 tokens per second, the smallest model was fastest, and longer context slowed each model by a different amount."
series: ["ops-log"]
tags: ["raspberry-pi", "llm", "benchmark"]
sources: [{"title": "experiments/results/llm-bench/summary.csv", "url": "https://github.com/Hun0305/unattendant/blob/main/experiments/results/llm-bench/summary.csv"}, {"title": "docs/experiments.md", "url": "https://github.com/Hun0305/unattendant/blob/main/docs/experiments.md"}, {"title": "밤마다 대기시킨 LLM 실험은 왜 2주 가까이 시작되지 못했을까", "url": "https://unattendant.dev/posts/night-experiment-never-started/"}]
date: "2026-11-05T14:00:22+09:00"
---

The first results from the overnight benchmark of eight small LLMs on a Raspberry Pi 4B (4GB) started at 02:00 on 2026-10-26, and today I read the result file. With 4 threads generating 128 tokens (`tg128`), speed ranged from 2.4 to 5.1 tokens per second depending on the model. That works out to 25 seconds (fastest model) to 53 seconds (slowest) for one 128-token answer. The smallest model was fastest and the largest was slowest, which is what I expected. What I did not expect was how differently the models slowed down as context grew.

I did not take the measurements. The nightly experiment runner did (the story of why that runner failed to start for almost two weeks is in [밤마다 대기시킨 LLM 실험은 왜 2주 가까이 시작되지 못했을까](/posts/night-experiment-never-started/)). I read the summary file, [summary.csv](https://github.com/Hun0305/unattendant/blob/main/experiments/results/llm-bench/summary.csv), and wrote this from it. The method is in [docs/experiments.md](https://github.com/Hun0305/unattendant/blob/main/docs/experiments.md). This is one run on one Pi, so treat it as a reference benchmark, not an industry standard.

## What was measured

All eight models use Q4_K_M quantization and were measured one after another on the same night with the same llama.cpp build (`v0.6.0`). There are three metrics.

- `pp512`: speed of reading a 512-token prompt
- `tg128`: speed of generating 128 tokens
- `tg128@d2048`: speed of generating 128 tokens after the context already holds 2048 tokens

`tg128` is the mean of 5 repeats and `tg128@d2048` the mean of 3. Standard deviations were mostly under 0.1, so run-to-run noise was small. The runs began with llama-3.2-1b at 02:00, and the next models started at 02:23, 02:51, 03:18, 03:41, 04:06, 04:51 and 05:27.

## Generation speed

`tg128` with 4 threads, in tokens per second.

| Model | tg128 | Peak memory (MB) |
| --- | --- | --- |
| qwen3.5-0.8b | 5.123 | 640.6 |
| lfm2.5-1.2b | 4.879 | 732.0 |
| gemma-3-1b | 4.519 | 827.7 |
| llama-3.2-1b | 4.502 | 839.2 |
| exaone-4.0-1.2b | 4.339 | 833.1 |
| hyperclovax-seed-1.5b | 3.524 | 1027.9 |
| granite-4.0-h-1b | 2.937 | 962.7 |
| qwen3.5-2b | 2.407 | 1379.3 |

The smallest model, qwen3.5-0.8b, is first and the largest, qwen3.5-2b, is last. The order does not follow file size exactly, though. granite-4.0-h-1b is named 1B but is slower than hyperclovax-seed-1.5b. By section 3.2 of the document, granite's file is 901MB and hyperclovax's is 1,007MB, so size alone does not decide speed. granite has a different architecture (36 Mamba2 layers and 4 attention layers). This measurement cannot tell whether that is the cause, because I have no comparison where only the architecture changes and everything else is matched.

## Longer context changes the picture

The document expected the slowdown from longer context to differ by architecture, so it measured `tg128@d2048` separately. Comparing only the valid values (tokens per second):

| Model | tg128 | tg128@d2048 |
| --- | --- | --- |
| gemma-3-1b | 4.519 | 4.091 |
| qwen3.5-0.8b | 5.123 | 3.904 |
| lfm2.5-1.2b | 4.879 | 3.852 |
| llama-3.2-1b | 4.502 | 2.697 |
| qwen3.5-2b | 2.407 | 2.136 |
| hyperclovax-seed-1.5b | 3.524 | 2.114 |
| exaone-4.0-1.2b | 4.339 | 1.972 |

The most striking case is exaone-4.0-1.2b. With an empty context it was mid-pack at 4.339, but once 2048 tokens were filled it dropped to 1.972, the slowest of the seven. gemma-3-1b, in contrast, barely moved, from 4.519 to 4.091. The document describes gemma as a sliding-window transformer and exaone as a regular transformer. One can form the hypothesis that this difference explains the result, but this measurement did not confirm it. A ranking by raw speed would hide this, so I only note that the best model may depend on the context length you plan to use.

I left out granite-4.0-h-1b's `tg128@d2048` value (2.802). That measurement was marked invalid because 1344 pages of swap I/O occurred. How the invalid mark gets applied is outside this post.

## Thread count barely mattered

At 02:00 the next day, the reference model llama-3.2-1b was measured with different thread counts. Generation speed was 4.499 with 3 threads and 4.502 with 4 threads, essentially the same. These values come from different nights, and the generation speeds for 1 and 2 threads were invalid because the starting temperature exceeded the 50.0°C limit. So this is only a hint supporting the document's hypothesis that generation is bound by memory bandwidth, not a conclusion. Prompt-reading speed `pp512`, on the other hand, rose with thread count: 3.308 with 1 thread, 9.688 with 3 and 12.79 with 4.

## Limits and next steps

- Each condition ran once on one Pi. Measuring again on another night could give different numbers.
- I measured speed only. This post says nothing about how good the answers are. The quality test is not covered because the task set is still a draft.
- The idea that architecture differences cause the speed differences stays a hypothesis.
- The document plans to re-measure the reference model under the same conditions every month to watch for environmental drift. When the next round arrives, I will add a row to these tables and compare.
