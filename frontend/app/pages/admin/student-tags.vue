<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">学员标签</h2>
        <p class="text-sm text-gray-500 mt-1">定义和管理的标签</p>
      </div>
      <button @click="openCreate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新增标签</button>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-3 font-medium">标签名称</th>
              <th class="px-4 py-3 font-medium">使用学员</th>
              <th class="px-4 py-3 font-medium">创建时间</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="t in tags" :key="t.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 font-medium text-gray-900">{{ t.name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ t.user_count || 0 }}</td>
              <td class="px-4 py-3 text-gray-500">{{ formatDt(t.created_at) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button @click="openEdit(t)" class="text-xs text-primary-600 hover:underline">编辑</button>
                  <button @click="handleDelete(t)" class="text-xs text-red-500 hover:underline">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="tags.length === 0 && !loading" class="px-4 py-12 text-center text-gray-400">暂无标签</div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <!-- Create Modal -->
    <div v-if="createOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeCreate">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">新增标签</h3>
        <input v-model="createName" @keyup.enter="doCreate" placeholder="标签名称" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" ref="createInputRef" />
        <div class="flex gap-2 mt-4">
          <button @click="doCreate" :disabled="!createName.trim()" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">创建</button>
          <button @click="closeCreate" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
        </div>
      </div>
    </div>

    <!-- Create Dirty Confirm -->
    <div v-if="createDirtyConfirm" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">放弃填写？</h3>
        <p class="text-sm text-gray-500 mb-4">已输入的内容将丢失。</p>
        <div class="flex gap-3">
          <button @click="forceCloseCreate" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button>
          <button @click="createDirtyConfirm = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续填写</button>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="editOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEdit">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">重命名标签</h3>
        <input v-model="editName" @keyup.enter="doEdit" placeholder="标签名称" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
        <div class="flex gap-2 mt-4">
          <button @click="doEdit" :disabled="!editName.trim() || editName === editingTag?.name" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">保存</button>
          <button @click="closeEdit" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
        </div>
      </div>
    </div>

    <!-- Edit Dirty Confirm -->
    <div v-if="editDirtyConfirm" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">放弃修改？</h3>
        <p class="text-sm text-gray-500 mb-4">已修改的内容将丢失。</p>
        <div class="flex gap-3">
          <button @click="forceCloseEdit" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button>
          <button @click="editDirtyConfirm = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续编辑</button>
        </div>
      </div>
    </div>

    <ConfirmModal :show="deleteOpen" title="删除标签" :message="`确定删除标签「${deletingTag?.name}」？`" variant="danger" @confirm="doDelete" @cancel="deleteOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();

const tags = ref([]);
const loading = ref(false);
const message = ref("");
const msgType = ref("success");
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const createOpen = ref(false);
const createName = ref("");
const createDirtyConfirm = ref(false);

const editOpen = ref(false);
const editName = ref("");
const editingTag = ref(null);
const editDirtyConfirm = ref(false);

const deleteOpen = ref(false);
const deletingTag = ref(null);

function formatDt(d) { if (!d) return ""; return d.substring(0, 16).replace("T", " "); }

async function fetchTags() {
  loading.value = true;
  try {
    const r = await $api.get("/tags");
    tags.value = r.data.data;
  } catch { showMessage("获取标签列表失败", "error"); } finally { loading.value = false; }
}

function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }

function openCreate() { createName.value = ""; createDirtyConfirm.value = false; createOpen.value = true; }
function closeCreate() {
  if (createName.value.trim()) { createDirtyConfirm.value = true; return; }
  createOpen.value = false;
}
function forceCloseCreate() { createDirtyConfirm.value = false; createOpen.value = false; }
async function doCreate() {
  if (!createName.value.trim()) return;
  try {
    await $api.post("/tags", { name: createName.value.trim() });
    createOpen.value = false;
    showMessage("标签已创建", "success");
    fetchTags();
  } catch (e) { showMessage(e.response?.data?.detail || "创建失败", "error"); }
}

function openEdit(t) {
  editingTag.value = t;
  editName.value = t.name;
  editDirtyConfirm.value = false;
  editOpen.value = true;
}
function closeEdit() {
  if (editName.value !== editingTag.value?.name) { editDirtyConfirm.value = true; return; }
  editOpen.value = false;
}
function forceCloseEdit() { editDirtyConfirm.value = false; editOpen.value = false; }
async function doEdit() {
  if (!editName.value.trim() || editName.value === editingTag.value?.name) return;
  try {
    await $api.patch(`/tags/${editingTag.value.id}`, { name: editName.value.trim() });
    editOpen.value = false;
    showMessage("标签已更新", "success");
    fetchTags();
  } catch (e) { showMessage(e.response?.data?.detail || "更新失败", "error"); }
}

function handleDelete(t) { deletingTag.value = t; deleteOpen.value = true; }
async function doDelete() {
  deleteOpen.value = false;
  try {
    await $api.delete(`/tags/${deletingTag.value.id}`);
    showMessage("标签已删除", "success");
    fetchTags();
  } catch (e) { showMessage(e.response?.data?.detail || "删除失败", "error"); }
}

fetchTags();
</script>
