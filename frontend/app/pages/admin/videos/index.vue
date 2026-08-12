<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">视频资料管理</h2>
        <p class="text-sm text-gray-500 mt-1">管理与播放教学视频资料</p>
      </div>
      <NuxtLink to="/admin/videos/add" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新增视频</NuxtLink>
    </div>

    <div class="mb-4">
      <input v-model="search" @input="onSearchInput" placeholder="搜索视频名称或描述..." class="w-full max-w-sm px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-gray-600"><tr><th class="px-4 py-3 font-medium">名称</th><th class="px-4 py-3 font-medium">文档库</th><th class="px-4 py-3 font-medium">时长</th><th class="px-4 py-3 font-medium">激活</th><th class="px-4 py-3 font-medium">观看</th><th class="px-4 py-3 font-medium">创建人</th><th class="px-4 py-3 font-medium">操作</th></tr></thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="item in items" :key="item.id" class="hover:bg-gray-50 transition">
            <td class="px-4 py-3 font-medium text-gray-900 max-w-xs truncate" :title="item.description">{{ item.name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ item.library_name || '-' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ fmtDur(item.duration_seconds) }}</td>
            <td class="px-4 py-3"><span :class="item.active ? 'text-green-600 bg-green-50 border border-green-200' : 'text-gray-400 bg-gray-50 border border-gray-200'" class="px-2 py-0.5 rounded text-xs">{{ item.active ? '启用' : '禁用' }}</span></td>
            <td class="px-4 py-3 text-gray-500 text-xs">{{ item.total_views }} 次 / {{ fmtDur(item.total_watch_seconds) }}</td>
            <td class="px-4 py-3 text-gray-500">{{ item.creator_name }}</td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <button @click="playVideo(item.id)" class="text-xs text-primary-600 hover:underline">播放</button>
                <NuxtLink :to="`/admin/videos/stats/${item.id}`" class="text-xs text-primary-600 hover:underline">统计</NuxtLink>
                <button @click="openEdit(item)" class="text-xs text-primary-600 hover:underline">编辑</button>
                <button @click="handleDelete(item)" class="text-xs text-red-500 hover:underline">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="items.length === 0 && !loading" class="px-4 py-12 text-center text-gray-400 text-sm">{{ search ? '没有匹配的视频' : '暂无视频资料' }}</div>
      <div class="px-4 py-3 border-t border-gray-100 flex items-center justify-between"><span class="text-sm text-gray-500">共 {{ total }} 条</span><div class="flex items-center gap-2"><button @click="page--; fetchList()" :disabled="page <= 1" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">上一页</button><span class="text-sm text-gray-500">第 {{ page }} / {{ totalPages }} 页</span><button @click="page++; fetchList()" :disabled="page >= totalPages" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">下一页</button></div></div>
    </div>

    <div v-if="editOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEdit">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">编辑视频</h3>
        <form @submit.prevent="handleEditSubmit" class="space-y-3">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">名称</label><input v-model="editForm.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">描述</label><textarea v-model="editForm.description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">文档库</label><select v-model="editForm.library_id" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"><option :value="null">无</option><option v-for="l in libraries" :key="l.id" :value="l.id">{{ l.name }}</option></select></div>
          <div><label class="flex items-center gap-2"><input type="checkbox" v-model="editForm.active" class="rounded" /><span class="text-sm text-gray-700">激活</span></label></div>
          <div class="flex gap-2 pt-2"><button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button><button type="button" @click="closeEdit" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg">取消</button></div>
        </form>
      </div>
    </div>
    <div v-if="editDirtyConfirm" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60"><div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center"><div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div><h3 class="text-lg font-bold text-gray-900 mb-2">放弃修改？</h3><p class="text-sm text-gray-500 mb-4">未保存的修改将丢失。</p><div class="flex gap-3"><button @click="forceCloseEdit" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button><button @click="editDirtyConfirm = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续编辑</button></div></div></div>

    <ConfirmModal :show="deleteOpen" title="删除视频" :message="`确定删除视频「${deletingItem?.name}」？`" sub-message="删除将同时移除相关观看记录和留言。" variant="danger" @confirm="confirmDelete" @cancel="deleteOpen = false" />

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();

const items = ref([]); const total = ref(0); const page = ref(1); const pageSize = 20; const loading = ref(false);
const search = ref(""); const message = ref(""); const msgType = ref("success"); const libraries = ref([]);
const editOpen = ref(false); const editForm = ref({}); const editSnapshot = ref({}); const editDirtyConfirm = ref(false); const editingItem = ref(null);
const deleteOpen = ref(false); const deletingItem = ref(null);
let searchTimer;

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1);
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");
const isEditDirty = computed(() => {
  const f = editForm.value; const s = editSnapshot.value;
  return f.name !== (s.name || "") || f.description !== (s.description || "") || f.library_id !== s.library_id || f.active !== s.active;
});

function fmtDur(s) { if (!s) return "0:00"; const m = Math.floor(s / 60); const r = s % 60; return `${m}:${String(r).padStart(2, "0")}`; }
function playVideo(id) { window.open(`/admin/videos/play/${id}`, "_blank", "width=1024,height=640"); }
function onSearchInput() { clearTimeout(searchTimer); searchTimer = setTimeout(() => { page.value = 1; fetchList(); }, 300); }

async function fetchList() {
  loading.value = true;
  try { const p = { page: page.value, page_size: pageSize }; if (search.value) p.search = search.value; const r = await $api.get("/videos", { params: p }); items.value = r.data.data.items; total.value = r.data.data.total; } catch {} finally { loading.value = false; }
}
async function fetchLibraries() { try { const r = await $api.get("/libraries"); libraries.value = r.data.data; } catch {} }

function openEdit(item) {
  editingItem.value = item; editForm.value = { name: item.name, description: item.description, library_id: item.library_id, active: item.active };
  editSnapshot.value = { ...editForm.value }; editDirtyConfirm.value = false; editOpen.value = true;
}
function closeEdit() { if (isEditDirty.value) { editDirtyConfirm.value = true; return; } editOpen.value = false; }
function forceCloseEdit() { editDirtyConfirm.value = false; editOpen.value = false; }
async function handleEditSubmit() {
  try {
    await $api.put(`/videos/${editingItem.value.id}`, { name: editForm.value.name, description: editForm.value.description, library_id: editForm.value.library_id, active: editForm.value.active });
    Object.assign(editingItem.value, editForm.value); showMessage("更新成功", "success"); editOpen.value = false;
  } catch (e) { showMessage(e.response?.data?.detail || "更新失败", "error"); }
}

function handleDelete(item) { deletingItem.value = item; deleteOpen.value = true; }
async function confirmDelete() {
  deleteOpen.value = false;
  try { await $api.delete(`/videos/${deletingItem.value.id}`, { data: { delete_oss: false } }); items.value = items.value.filter(i => i.id !== deletingItem.value.id); total.value--; showMessage("已删除", "success"); } catch (e) { showMessage(e.response?.data?.detail || "删除失败", "error"); }
}

function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }

fetchLibraries(); fetchList();
</script>
