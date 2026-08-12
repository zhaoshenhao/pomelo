<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">学习资料管理</h2>
        <p class="text-sm text-gray-500 mt-1">生成和管理基于文档库的学习资料</p>
      </div>
      <NuxtLink to="/admin/study-materials/generate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新建学习资料</NuxtLink>
    </div>

    <div class="mb-4">
      <input v-model="search" @input="onSearchInput" placeholder="搜索学习资料名称..."
        class="w-full max-w-sm px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-3 font-medium">名称</th>
              <th class="px-4 py-3 font-medium">描述</th>
              <th class="px-4 py-3 font-medium">文档库</th>
              <th class="px-4 py-3 font-medium">文档</th>
              <th class="px-4 py-3 font-medium">创建人</th>
              <th class="px-4 py-3 font-medium">创建日期</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="item in items" :key="item.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{{ item.name }}</td>
              <td class="px-4 py-3 text-gray-500 max-w-xs truncate">{{ item.description || '-' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ item.library_name }}</td>
              <td class="px-4 py-3 text-gray-400 text-xs max-w-xs truncate">{{ item.document_names || '-' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ item.creator_name }}</td>
              <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(item.created_at) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <NuxtLink :to="`/admin/study-materials/${item.id}`" class="text-xs text-primary-600 hover:underline">查看</NuxtLink>
                  <NuxtLink :to="`/admin/study-materials/stats/${item.id}`" class="text-xs text-primary-600 hover:underline">统计</NuxtLink>
                  <button @click="openEdit(item)" class="text-xs text-primary-600 hover:underline">编辑</button>
                  <button @click="openVoiceModal(item)" class="text-xs text-accent-600 hover:underline">配音</button>
                  <button @click="handleDelete(item)" class="text-xs text-red-500 hover:underline">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="items.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">{{ search ? '没有匹配的学习资料' : '暂无学习资料' }}</div>

      <div class="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
        <span class="text-sm text-gray-500">共 {{ total }} 条</span>
        <div class="flex items-center gap-2">
          <button @click="page--; fetchList()" :disabled="page <= 1" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">上一页</button>
          <span class="text-sm text-gray-500">第 {{ page }} / {{ totalPages }} 页</span>
          <button @click="page++; fetchList()" :disabled="page >= totalPages" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">下一页</button>
        </div>
      </div>
    </div>

    <div v-if="editModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEditModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">编辑学习资料</h3>
        <form @submit.prevent="handleEditSubmit" class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input v-model="editForm.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea v-model="editForm.description" rows="3" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"></textarea>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-xs text-gray-500 mb-1">最少阅读(分钟)</label><input v-model.number="editForm.min_minutes" type="number" min="1" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
            <div class="flex items-center gap-2 pt-5"><input type="checkbox" v-model="editForm.active" class="w-3.5 h-3.5" /><label class="text-xs text-gray-500">活跃课程</label></div>
          </div>
          <div class="text-xs text-gray-400">阅读次数：{{ editingItem?.read_count || 0 }} | 完成次数：{{ editingItem?.complete_count || 0 }}</div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button>
            <button type="button" @click="closeEditModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="voiceModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeVoiceModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">配音设置</h3>
        <div class="space-y-3 text-sm">
          <div><span class="text-gray-500">名称：</span>{{ voicingItem?.name }}</div>
          <div><span class="text-gray-500">描述：</span>{{ voicingItem?.description || '-' }}</div>
          <div><span class="text-gray-500">当前配音角色：</span>{{ voicingItem?.voice || '未配音' }}</div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">选择新角色</label>
            <select v-model="voiceForm.voice" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400">
              <option value="" disabled>请选择配音角色</option>
              <option v-for="v in availableVoices" :key="v" :value="v">{{ v }}</option>
            </select>
          </div>
        </div>
        <div class="flex gap-2 pt-4">
          <button @click="handleVoiceSubmit" :disabled="!voiceForm.voice || voicing"
            class="flex-1 py-2 bg-accent-600 text-white text-sm rounded-lg hover:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ voicing ? '配音中...' : '确认配音' }}
          </button>
          <button @click="closeVoiceModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
        </div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <div v-if="editConfirmClose" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">放弃修改？</h3>
        <p class="text-sm text-gray-500 mb-4">你有未保存的修改，关闭后将丢失。</p>
        <div class="flex gap-3">
          <button @click="forceCloseEdit" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button>
          <button @click="editConfirmClose = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续编辑</button>
        </div>
      </div>
    </div>

    <ConfirmModal :show="deleteOpen" title="删除学习资料" :message="`确定删除学习资料「${deletingItem?.name}」？同时会删除磁盘上的生成文件。`" variant="danger" @confirm="confirmDelete" @cancel="deleteOpen = false" />

    <ConfirmModal :show="voiceConfirmOpen" title="确认配音" :message="`将为「${voicingItem?.name}」生成配音（${voiceForm.voice}）。如果已有配音文件，会被覆盖。确定继续？`" variant="danger" @confirm="doVoice" @cancel="voiceConfirmOpen = false" />

    <div v-if="voicing" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">正在配音，请稍候...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();

const items = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const search = ref("");
const message = ref("");
const msgType = ref("success");
const deleteOpen = ref(false);
const deletingItem = ref(null);
const editModalOpen = ref(false);
const editingItem = ref(null);
const editForm = ref({ name: "", description: "" });
const editFormSnapshot = ref({});
const editConfirmClose = ref(false);
const voiceModalOpen = ref(false);
const voicingItem = ref(null);
const voiceForm = ref({ voice: "" });
const availableVoices = ref([]);
const voiceConfirmOpen = ref(false);
const voicing = ref(false);

let searchTimer = null;

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1);
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const isEditDirty = computed(() => {
  return editForm.value.name !== editFormSnapshot.value.name
    || editForm.value.description !== (editFormSnapshot.value.description || "")
    || editForm.value.min_minutes !== editFormSnapshot.value.min_minutes
    || editForm.value.active !== editFormSnapshot.value.active;
});

function formatDate(d) {
  if (!d) return "";
  return d.substring(0, 16).replace("T", " ");
}

async function fetchList() {
  try {
    const params = { page: page.value, page_size: pageSize };
    if (search.value) params.search = search.value;
    const res = await $api.get("/study-materials", { params });
    const d = res.data.data;
    items.value = d.items;
    total.value = d.total;
  } catch (e) {
    items.value = [];
    total.value = 0;
  }
}

function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { page.value = 1; fetchList(); }, 300);
}

function openEdit(item) {
  editingItem.value = item;
  editForm.value = { name: item.name, description: item.description, min_minutes: item.min_minutes || 10, active: item.active !== undefined ? item.active : true };
  editFormSnapshot.value = { name: item.name, description: item.description || "", min_minutes: item.min_minutes || 10, active: item.active !== undefined ? item.active : true };
  editConfirmClose.value = false;
  editModalOpen.value = true;
}

function closeEditModal() {
  if (isEditDirty.value) {
    editConfirmClose.value = true;
  } else {
    editModalOpen.value = false;
  }
}

function forceCloseEdit() {
  editConfirmClose.value = false;
  editModalOpen.value = false;
}

async function handleEditSubmit() {
  try {
    await $api.put(`/study-materials/${editingItem.value.id}`, editForm.value);
    editingItem.value.name = editForm.value.name;
    editingItem.value.description = editForm.value.description;
    editingItem.value.min_minutes = editForm.value.min_minutes;
    editingItem.value.active = editForm.value.active;
    showMessage("更新成功", "success");
    editConfirmClose.value = false;
    editModalOpen.value = false;
  } catch (e) {
    showMessage(e.response?.data?.detail || "更新失败", "error");
  }
}

function handleDelete(item) {
  deletingItem.value = item;
  deleteOpen.value = true;
}

async function confirmDelete() {
  const item = deletingItem.value;
  deleteOpen.value = false;
  try {
    await $api.delete(`/study-materials/${item.id}`);
    items.value = items.value.filter((m) => m.id !== item.id);
    total.value--;
    showMessage("已删除", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "删除失败", "error");
  }
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

async function fetchVoices() {
  try {
    const res = await $api.get("/study-materials/voices");
    availableVoices.value = res.data.data.voices;
    if (!voiceForm.value.voice && res.data.data.default) {
      voiceForm.value.voice = res.data.data.default;
    }
  } catch {
    availableVoices.value = [];
    voiceForm.value.voice = "";
    showMessage("配音角色加载失败，请刷新重试", "error");
  }
}

function openVoiceModal(item) {
  voicingItem.value = item;
  voiceForm.value.voice = "";
  voiceConfirmOpen.value = false;
  voicing.value = false;
  voiceModalOpen.value = true;
  fetchVoices();
}

function closeVoiceModal() {
  if (!voicing.value) voiceModalOpen.value = false;
}

function handleVoiceSubmit() {
  if (!voiceForm.value.voice) return;
  voiceConfirmOpen.value = true;
}

async function doVoice() {
  voiceConfirmOpen.value = false;
  voicing.value = true;
  try {
    await $api.post(`/study-materials/${voicingItem.value.id}/voice`, { voice: voiceForm.value.voice });
    voicingItem.value.voice = voiceForm.value.voice;
    showMessage("配音完成", "success");
    voiceModalOpen.value = false;
  } catch (e) {
    showMessage(e.response?.data?.detail || "配音失败", "error");
  } finally {
    voicing.value = false;
  }
}

fetchList();
</script>
