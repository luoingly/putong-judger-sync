<script setup lang="ts">
import problems from '@/data/problems.json'
import ranklist from '@/data/ranklist.json'

const problemLabels = new Map(problems.map(p => [ p.problemId, p.title ]))

function getProblem (item: (typeof ranklist)[number], problemId: string) {
  return item.problems[problemId as keyof typeof item.problems]
}

function thousandSeparator (num: number | string): string {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}
</script>

<template>
  <div class="px-0 py-4">
    <div class="mt-4 overflow-x-auto">
      <table class="font-verdana min-w-full table-fixed">
        <thead>
          <tr class="h-16">
            <th class="border border-l-0 min-w-20">
              <i class="pi pi-hashtag" />
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
              class="border min-w-20 p-2 text-sm"
            >
              {{ problemLabels.get(problem.problemId) }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(item, index) in ranklist" :key="index" class="h-16 hover:bg-emphasis transition-colors">
            <td class="border border-l-0">
              {{ item.rank }}
            </td>
            <td class="border font-sans overflow-hidden text-ellipsis whitespace-nowrap">
              {{ item.name }}
            </td>
            <td class="border">
              {{ item.solvedCount }}
            </td>
            <td class="border">
              {{ thousandSeparator(item.completionTokens) }}
            </td>

            <template v-for="{ problemId: p } in problems">
              <td v-if="!getProblem(item, p) || !getProblem(item, p)!.isSolved" :key="`${p}-1`" class="border" />
              <td
                v-else :key="`${p}-2`" class="border cursor-pointer transition-colors" :class="[
                  getProblem(item, p)!.isFirstSolved
                    ? 'bg-sky-600/90 hover:bg-sky-700/90'
                    : 'bg-green-500/90 hover:bg-green-600/85',
                ]"
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
    </div>
  </div>
</template>

<style scoped>
table th,
table td {
  padding: 8px 12px;
  text-align: center;
  border-color: var(--p-content-border-color);
}
</style>
