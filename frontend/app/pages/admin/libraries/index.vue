<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">文档库管理</h2>
        <p class="text-sm text-gray-500 mt-1">管理所有文档库</p>
      </div>
      <button @click="openCreate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新建文档库</button>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-3 font-medium">ID</th>
              <th class="px-4 py-3 font-medium">名称</th>
              <th class="px-4 py-3 font-medium">目录</th>
              <th class="px-4 py-3 font-medium">描述</th>
              <th class="px-4 py-3 font-medium">创建时间</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="lib in libraries" :key="lib.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 text-gray-500">{{ lib.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">
                <NuxtLink :to="`/admin/libraries/${lib.id}`" class="text-primary-600 hover:underline">{{ lib.name }}</NuxtLink>
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs font-mono">{{ dirName(lib.local_path) }}</td>
              <td class="px-4 py-3 text-gray-500 max-w-xs truncate">{{ lib.description || '-' }}</td>
              <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(lib.created_at) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <NuxtLink :to="`/admin/libraries/${lib.id}`" class="text-xs text-primary-600 hover:underline">管理</NuxtLink>
                  <button @click="openEdit(lib)" class="text-xs text-primary-600 hover:underline">编辑</button>
                  <button @click="handleDelete(lib)" class="text-xs text-red-500 hover:underline">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="libraries.length === 0" class="px-4 py-12 text-center text-gray-400">暂无文档库，点击"新建文档库"开始</div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <!-- Form Modal -->
    <div v-if="modalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingLib ? '编辑文档库' : '新建文档库' }}</h3>
        <form @submit.prevent="handleSubmit" class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名称 <span class="text-red-500">*</span></label>
            <input v-model="form.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">目录名称</label>
            <input ref="directoryInput" v-model="form.directory" :placeholder="editingLib ? '' : '留空默认使用文档库名称'" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea v-model="form.description" rows="3" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"></textarea>
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button>
            <button type="button" @click="closeModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmModal :show="deleteLibModalOpen" title="删除文档库" :message="`确定删除文档库「${deletingLib?.name}」？`" subMessage="该操作会清空库内所有文档，不可恢复。" variant="danger" @confirm="doDeleteLib" @cancel="deleteLibModalOpen = false" />

    <!-- Delete Library Confirmation Modal -->
    <div v-if="deleteLibModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="deleteLibModalOpen = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-3">删除文档库</h3>
        <p class="text-sm text-gray-600 mb-1">确定删除文档库「{{ deletingLib?.name }}」？</p>
        <p class="text-xs text-gray-400 mb-4">该操作会清空库内所有文档，不可恢复。</p>
        <label class="flex items-center gap-2 mb-2 cursor-pointer">
          <input type="checkbox" v-model="deleteLibDir" class="w-4 h-4 text-primary-600 border-gray-300 rounded" />
          <span class="text-sm text-gray-600">同时删除磁盘上的目录</span>
        </label>
        <label class="flex items-center gap-2 mb-3 cursor-pointer">
          <input type="checkbox" v-model="forceDelete" class="w-4 h-4 text-red-600 border-gray-300 rounded" />
          <span class="text-sm text-red-600">强制删除（用于破损文档库，忽略磁盘清理错误）</span>
        </label>
        <div class="flex gap-2">
          <button @click="doDeleteLib" class="flex-1 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700">删除</button>
          <button @click="deleteLibModalOpen = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
        </div>
      </div>
    </div>

    <ConfirmModal v-if="dirConflictOpen" :show="dirConflictOpen" title="目录已存在" :message="dirConflictMessage" variant="primary" confirmText="使用已存在目录" cancelText="使用新目录名" @confirm="onDirConflictConfirm" @cancel="onDirConflictCancel" />

    <div v-if="confirmCloseOpen" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">{{ editingLib ? '放弃修改？' : '放弃填写？' }}</h3>
        <p class="text-sm text-gray-500 mb-4">{{ editingLib ? '你有未保存的修改，关闭后将丢失。' : '已输入的内容将丢失。' }}</p>
        <div class="flex gap-3">
          <button @click="forceClose" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button>
          <button @click="confirmCloseOpen = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续{{ editingLib ? '编辑' : '填写' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();

const libraries = ref([]);
const modalOpen = ref(false);
const editingLib = ref(null);
const form = ref({ name: "", description: "", directory: "" });
const directoryInput = ref(null);
const message = ref("");
const msgType = ref("success");
const deleteLibModalOpen = ref(false);
const deletingLib = ref(null);
const deleteLibDir = ref(false);
const forceDelete = ref(false);
const dirConflictOpen = ref(false);
const dirConflictMessage = ref("");
const formSnapshot = ref({ name: "", description: "", directory: "" });
const confirmCloseOpen = ref(false);

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const isEditDirty = computed(() => {
  return form.value.name !== formSnapshot.value.name
    || form.value.description !== formSnapshot.value.description
    || form.value.directory !== formSnapshot.value.directory;
});

const isCreateDirty = computed(() => {
  return !!form.value.name || !!form.value.description || !!form.value.directory;
});

const isDirty = computed(() => editingLib.value ? isEditDirty.value : isCreateDirty.value);

async function fetchLibraries() {
  try {
    const res = await $api.get("/libraries");
    libraries.value = res.data.data;
  } catch {
    showMessage("获取文档库列表失败", "error");
  }
}

function dirName(path) {
  if (!path) return "-";
  return path.replace(/[/\\]+$/, "").split("/").pop().split("\\").pop();
}

function openCreate() {
  editingLib.value = null;
  form.value = { name: "", description: "", directory: "" };
  formSnapshot.value = { name: "", description: "", directory: "" };
  confirmCloseOpen.value = false;
  modalOpen.value = true;
}

function openEdit(lib) {
  editingLib.value = lib;
  form.value = { name: lib.name, description: lib.description || "", directory: dirName(lib.local_path) };
  formSnapshot.value = { name: lib.name, description: lib.description || "", directory: dirName(lib.local_path) };
  confirmCloseOpen.value = false;
  modalOpen.value = true;
}

function closeModal() {
  if (isDirty.value) {
    confirmCloseOpen.value = true;
  } else {
    modalOpen.value = false;
  }
}

function forceClose() {
  confirmCloseOpen.value = false;
  modalOpen.value = false;
}

async function submitCreate(useExisting) {
  try {
    const payload = { name: form.value.name, description: form.value.description, directory: form.value.directory, use_existing_directory: useExisting };
    const res = await $api.post("/libraries", payload);
    libraries.value.push(res.data.data);
    showMessage("创建成功", "success");
    modalOpen.value = false;
    dirConflictOpen.value = false;
  } catch (e) {
    const detail = e.response?.data?.detail || "";
    if (e.response?.status === 409 && /已存在/.test(detail) && !useExisting) {
      dirConflictMessage.value = detail;
      dirConflictOpen.value = true;
    } else {
      showMessage(detail || "操作失败", "error");
    }
  }
}

function onDirConflictConfirm() {
  submitCreate(true);
}

function onDirConflictCancel() {
  dirConflictOpen.value = false;
  showMessage("请使用新的目录名称后重新提交", "error");
  nextTick(() => { directoryInput.value?.focus(); });
}

async function handleSubmit() {
  if (editingLib.value) {
    try {
      const payload = { name: form.value.name, description: form.value.description, directory: form.value.directory || undefined };
      const res = await $api.put(`/libraries/${editingLib.value.id}`, payload);
      Object.assign(editingLib.value, res.data.data);
      showMessage("更新成功", "success");
      modalOpen.value = false;
    } catch (e) {
      showMessage(e.response?.data?.detail || "操作失败", "error");
    }
    return;
  }
  await submitCreate(false);
}

function handleDelete(lib) {
  deletingLib.value = lib;
  deleteLibDir.value = false;
  forceDelete.value = false;
  deleteLibModalOpen.value = true;
}

async function doDeleteLib() {
  deleteLibModalOpen.value = false;
  const lib = deletingLib.value;
  try {
    await $api.delete(`/libraries/${lib.id}`, { params: { delete_directory: deleteLibDir.value, force: forceDelete.value } });
    libraries.value = libraries.value.filter((l) => l.id !== lib.id);
    const dirLabel = deleteLibDir.value ? (forceDelete.value ? "（目录已尽可能清理）" : "（目录已清理）") : "（目录已保留在磁盘）";
    showMessage("已删除" + dirLabel, "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "删除失败", "error");
  }
}

function formatDate(dateStr) {
  return dateStr ? dateStr.substring(0, 10) : "";
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

fetchLibraries();
</script>
