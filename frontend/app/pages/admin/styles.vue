<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">改写风格管理</h2>
        <p class="text-sm text-gray-500 mt-1">管理自定义改写风格的 Prompt</p>
      </div>
      <button @click="openCreate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新建风格</button>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-3 font-medium">ID</th>
              <th class="px-4 py-3 font-medium">名称</th>
              <th class="px-4 py-3 font-medium">Prompt</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="style in styles" :key="style.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 text-gray-500">{{ style.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">{{ style.name }}</td>
              <td class="px-4 py-3 text-gray-500 max-w-md truncate text-xs font-mono">{{ style.prompt }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button @click="openEdit(style)" class="text-xs text-primary-600 hover:underline">编辑</button>
                  <button @click="handleDelete(style)" class="text-xs text-red-500 hover:underline">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="styles.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无改写风格</div>
    </div>

    <div v-if="modalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingStyle ? '编辑改写风格' : '新建改写风格' }}</h3>
        <form @submit.prevent="handleSubmit" class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名称 <span class="text-red-500">*</span></label>
            <input v-model="form.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Prompt <span class="text-red-500">*</span></label>
            <textarea v-model="form.prompt" required rows="6" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 font-mono"></textarea>
            <p class="text-xs text-gray-400 mt-1">AI 改写时使用的完整 Prompt 文本，文档内容会拼接在 Prompt 之后</p>
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button>
            <button type="button" @click="closeModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <ConfirmModal :show="deleteModalOpen" title="删除改写风格" :message="`确定删除改写风格「${deletingStyle?.name}」？`" variant="danger" @confirm="confirmDelete" @cancel="deleteModalOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "admin"] });

const { $api } = useNuxtApp();

const styles = ref([]);
const modalOpen = ref(false);
const editingStyle = ref(null);
const form = ref({ name: "", prompt: "" });
const message = ref("");
const msgType = ref("success");
const deleteModalOpen = ref(false);
const deletingStyle = ref(null);

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

async function fetchStyles() {
  try {
    const res = await $api.get("/rewrite-styles");
    styles.value = res.data.data;
  } catch {
    showMessage("获取改写风格列表失败", "error");
  }
}

function openCreate() {
  editingStyle.value = null;
  form.value = { name: "", prompt: "" };
  modalOpen.value = true;
}

function openEdit(style) {
  editingStyle.value = style;
  form.value = { name: style.name, prompt: style.prompt };
  modalOpen.value = true;
}

function closeModal() {
  modalOpen.value = false;
}

async function handleSubmit() {
  if (editingStyle.value) {
    try {
      const res = await $api.put(`/rewrite-styles/${editingStyle.value.id}`, form.value);
      Object.assign(editingStyle.value, res.data.data);
      showMessage("更新成功", "success");
      modalOpen.value = false;
    } catch (e) {
      showMessage(e.response?.data?.detail || "更新失败", "error");
    }
  } else {
    try {
      const res = await $api.post("/rewrite-styles", form.value);
      styles.value.push(res.data.data);
      showMessage("创建成功", "success");
      modalOpen.value = false;
    } catch (e) {
      showMessage(e.response?.data?.detail || "创建失败", "error");
    }
  }
}

function handleDelete(style) {
  deletingStyle.value = style;
  deleteModalOpen.value = true;
}

async function confirmDelete() {
  const style = deletingStyle.value;
  deleteModalOpen.value = false;
  try {
    await $api.delete(`/rewrite-styles/${style.id}`);
    styles.value = styles.value.filter((s) => s.id !== style.id);
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

fetchStyles();
</script>
