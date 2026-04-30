<script setup lang="ts">
import { computed } from 'vue'
import problems from '@/data/problems.json'
import ranklist from '@/data/ranklist.json'

const problemLabels = new Map(problems.map(p => [ p.problemId, p.title ]))

function getProblem (item: (typeof ranklist)[number], problemId: string) {
  return item.problems[problemId as keyof typeof item.problems]
}

function thousandSeparator (num: number | string): string {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

// Per-problem min/max tokens among solved entries
const problemTokenRange = computed(() => {
  const ranges: Record<string, { min: number, max: number }> = {}
  for (const { problemId } of problems) {
    const tokens: number[] = []
    for (const item of ranklist) {
      const p = getProblem(item, problemId)
      if (p?.isSolved && p.completionTokens > 0) {
        tokens.push(p.completionTokens)
      }
    }
    if (tokens.length > 0) {
      ranges[problemId] = { min: Math.min(...tokens), max: Math.max(...tokens) }
    }
  }
  return ranges
})

function getTokenColor (problemId: string, tokens: number): string {
  const B = [ 0.448, 0.119, 151.328 ]
  const A = [ 0.627, 0.194, 149.214 ]

  const range = problemTokenRange.value[problemId]
  if (!range || range.max === range.min) return `oklch(${B[0]} ${B[1]} ${B[2]})`

  const ratio = (tokens - range.min) / (range.max - range.min)
  return `oklch(${A[0] + ratio * (B[0] - A[0])} ${A[1] + ratio * (B[1] - A[1])} ${A[2] + ratio * (B[2] - A[2])})`
}
</script>

<template>
  <table class="bg- font-verdana min-w-full table-fixed">
    <thead>
      <tr class="h-16">
        <th class="border border-l-0 min-w-20">
          #
        </th>
        <th class="border max-w-36">
          Model
        </th>
        <th class="border min-w-22">
          Solved
        </th>
        <th class="border min-w-24">
          Tokens
        </th>

        <th
          v-for="problem in problems" :key="problem.problemId" v-tooltip.bottom="problem.title"
          class="border last:border-r-0 min-w-20 p-2"
        >
          <span class="block text-sm">
            {{ problemLabels.get(problem.problemId) }}
          </span>
          <span class="block font-light text-muted-color text-xs">
            {{ problem.problemId }}
          </span>
        </th>
      </tr>
    </thead>

    <tbody>
      <tr v-for="(item, index) in ranklist" :key="index" class="h-16 hover:bg-emphasis transition-colors">
        <td class="border border-l-0">
          {{ item.rank }}
        </td>
        <td class="border whitespace-nowrap">
          <span class="block">
            {{ item.model }}
          </span>
          <span class="block font-light text-muted-color text-sm">
            {{ item.extraInfo }}
          </span>
        </td>
        <td class="border">
          {{ item.solvedCount }}
        </td>
        <td class="border">
          {{ thousandSeparator(item.completionTokens) }}
        </td>

        <template v-for="{ problemId: p } in problems">
          <td v-if="!getProblem(item, p) || !getProblem(item, p)!.isSolved" :key="`${p}-1`" class="border last:border-r-0" />
          <td
            v-else :key="`${p}-2`" class="border last:border-r-0 transition-colors"
            :style="{ backgroundColor: getTokenColor(p, getProblem(item, p)!.completionTokens) }"
          >
            <span class="block font-bold text-white w-full">+</span>
            <span class="block text-sm text-white w-full">
              {{ thousandSeparator(getProblem(item, p)!.completionTokens) }}
            </span>
          </td>
        </template>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table th,
table td {
  padding: 8px 12px;
  text-align: center;
  border-color: var(--p-content-border-color);
}
</style>
