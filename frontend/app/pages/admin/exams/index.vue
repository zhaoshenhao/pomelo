<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">试卷管理</h2>
        <p class="text-sm text-gray-500 mt-1">从题库组卷、安排考试、查看成绩</p>
      </div>
      <NuxtLink to="/admin/exams/generate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 生成试卷</NuxtLink>
    </div>

    <div class="mb-4"><input v-model="search" @input="onSearchInput" placeholder="搜索试卷名称..." class="w-full max-w-sm px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <table class="w-full text-sm"><thead class="bg-gray-50 text-left text-gray-600"><tr><th class="px-4 py-3 font-medium">名称</th><th class="px-4 py-3 font-medium">描述</th><th class="px-4 py-3 font-medium">时长(分)</th><th class="px-4 py-3 font-medium">及格分</th><th class="px-4 py-3 font-medium">生成人</th><th class="px-4 py-3 font-medium">生成日期</th><th class="px-4 py-3 font-medium">操作</th></tr></thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="item in items" :key="item.id" class="hover:bg-gray-50 transition">
            <td class="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{{ item.name }}</td>
            <td class="px-4 py-3 text-gray-500 max-w-xs truncate">{{ item.description || '-' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ item.duration_minutes }}</td>
            <td class="px-4 py-3 text-gray-500">{{ item.pass_score }}</td>
            <td class="px-4 py-3 text-gray-500">{{ item.creator_name }}</td>
            <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(item.created_at) }}</td>
            <td class="px-4 py-3"><div class="flex items-center gap-2">
              <NuxtLink :to="`/admin/exams/${item.id}/browse`" class="text-xs text-primary-600 hover:underline">浏览</NuxtLink>
              <button @click="openEdit(item)" class="text-xs text-primary-600 hover:underline">编辑</button>
              <NuxtLink :to="`/admin/exams/${item.id}/schedule`" class="text-xs text-primary-600 hover:underline">安排</NuxtLink>
              <NuxtLink :to="`/admin/exams/${item.id}/results`" class="text-xs text-primary-600 hover:underline">成绩</NuxtLink>
              <button @click="handleDelete(item)" class="text-xs text-red-500 hover:underline">删除</button>
            </div></td>
          </tr>
        </tbody>
      </table>
      <div v-if="items.length === 0 && !loading" class="px-4 py-12 text-center text-gray-400 text-sm">{{ search ? '没有匹配的试卷' : '暂无试卷' }}</div>
      <div class="px-4 py-3 border-t border-gray-100 flex items-center justify-between"><span class="text-sm text-gray-500">共 {{ total }} 条</span><div class="flex items-center gap-2"><button @click="page--; fetchList()" :disabled="page <= 1" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">上一页</button><span class="text-sm text-gray-500">第 {{ page }} / {{ totalPages }} 页</span><button @click="page++; fetchList()" :disabled="page >= totalPages" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">下一页</button></div></div>
    </div>

    <div v-if="editModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEdit">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6"><h3 class="text-lg font-bold text-gray-900 mb-4">编辑试卷</h3>
        <form @submit.prevent="handleEditSubmit" class="space-y-3">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">名称</label><input v-model="editForm.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">描述</label><textarea v-model="editForm.description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea></div>
          <div class="grid grid-cols-2 gap-3"><div><label class="block text-xs text-gray-500 mb-1">时长(分)</label><input v-model.number="editForm.duration_minutes" type="number" min="1" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div><div><label class="block text-xs text-gray-500 mb-1">及格分</label><input v-model.number="editForm.pass_score" type="number" min="1" max="100" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div></div>
          <div class="flex gap-2 pt-2"><button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button><button type="button" @click="closeEdit" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg">取消</button></div>
        </form>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
    <ConfirmModal :show="deleteOpen" title="删除试卷" message="确定删除？同时会删除所有安排记录和试卷目录。" variant="danger" @confirm="confirmDelete" @cancel="deleteOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const items = ref([]); const total = ref(0); const page = ref(1); const pageSize = 20; const loading = ref(false);
const search = ref(""); const message = ref(""); const msgType = ref("success");
const deleteOpen = ref(false); const deletingItem = ref(null);
const editModalOpen = ref(false); const editingItem = ref(null); const editForm = ref({});
let searchTimer;
const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1);
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700");

function formatDate(d) { if (!d) return ""; return d.substring(0, 16).replace("T", " "); }
function onSearchInput() { clearTimeout(searchTimer); searchTimer = setTimeout(() => { page.value = 1; fetchList(); }, 300); }
async function fetchList() { loading.value = true; try { const p = { page: page.value, page_size: pageSize }; if (search.value) p.search = search.value; const r = await $api.get("/exams", { params: p }); items.value = r.data.data.items; total.value = r.data.data.total; } catch {} finally { loading.value = false; } }
function openEdit(item) { editingItem.value = item; editForm.value = { name: item.name, description: item.description, duration_minutes: item.duration_minutes, pass_score: item.pass_score }; editModalOpen.value = true; }
function closeEdit() { editModalOpen.value = false; }
async function handleEditSubmit() { try { await $api.put(`/exams/${editingItem.value.id}`, editForm.value); Object.assign(editingItem.value, editForm.value); showMessage("更新成功", "success"); editModalOpen.value = false; } catch (e) { showMessage(e.response?.data?.detail || "更新失败", "error"); } }
function handleDelete(item) { deletingItem.value = item; deleteOpen.value = true; }
async function confirmDelete() { deleteOpen.value = false; try { await $api.delete(`/exams/${deletingItem.value.id}`); items.value = items.value.filter(i => i.id !== deletingItem.value.id); total.value--; showMessage("已删除", "success"); } catch (e) { showMessage(e.response?.data?.detail || "删除失败", "error"); } }
function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }
fetchList();
</script>
