<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">AI提示词管理</h2>
        <p class="text-sm text-gray-500 mt-1">管理不同功能的 AI 提示词（改写、学习资料、试题）</p>
      </div>
      <button @click="openCreate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新建提示词</button>
    </div>

    <div class="flex items-center gap-2 mb-4">
      <button
        v-for="t in filterOptions"
        :key="t.value"
        @click="typeFilter = t.value; fetchPrompts()"
        class="px-3 py-1.5 text-xs rounded-full border transition"
        :class="typeFilter === t.value ? 'bg-primary-50 text-primary-700 border-primary-300' : 'border-gray-200 text-gray-500 hover:bg-gray-50'"
      >{{ t.label }}</button>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-3 font-medium">ID</th>
              <th class="px-4 py-3 font-medium">名称</th>
              <th class="px-4 py-3 font-medium">类型</th>
              <th class="px-4 py-3 font-medium">Prompt</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="prompt in prompts" :key="prompt.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 text-gray-500">{{ prompt.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">{{ prompt.name }}</td>
              <td class="px-4 py-3">
                <span class="text-xs px-2 py-0.5 rounded-full border" :class="typeBadge(prompt.prompt_type)">{{ typeLabel(prompt.prompt_type) }}</span>
              </td>
              <td class="px-4 py-3 text-gray-500 max-w-md truncate text-xs font-mono">{{ prompt.prompt }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button @click="openEdit(prompt)" class="text-xs text-primary-600 hover:underline">编辑</button>
                  <button @click="handleDelete(prompt)" class="text-xs text-red-500 hover:underline">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="prompts.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无提示词</div>
    </div>

    <div v-if="modalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingPrompt ? '编辑提示词' : '新建提示词' }}</h3>
        <form @submit.prevent="handleSubmit" class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">类型 <span class="text-red-500">*</span></label>
            <select v-model="form.prompt_type" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400">
              <option value="rewrite">改写</option>
              <option value="study">学习资料</option>
              <option value="exam">试题</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名称 <span class="text-red-500">*</span></label>
            <input v-model="form.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Prompt <span class="text-red-500">*</span></label>
            <textarea v-model="form.prompt" required rows="6" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 font-mono"></textarea>
            <p class="text-xs text-gray-400 mt-1">文档内容会拼接在 Prompt 之后发送给 AI</p>
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button>
            <button type="button" @click="closeModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <div v-if="confirmClose" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">{{ editingPrompt ? '放弃修改？' : '放弃填写？' }}</h3>
        <p class="text-sm text-gray-500 mb-4">{{ editingPrompt ? '你有未保存的修改，关闭后将丢失。' : '已输入的内容将丢失。' }}</p>
        <div class="flex gap-3">
          <button @click="forceClose" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">{{ editingPrompt ? '放弃并关闭' : '放弃并关闭' }}</button>
          <button @click="confirmClose = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">{{ editingPrompt ? '继续编辑' : '继续填写' }}</button>
        </div>
      </div>
    </div>

    <ConfirmModal :show="deleteModalOpen" title="删除提示词" :message="`确定删除提示词「${deletingPrompt?.name}」？`" variant="danger" @confirm="confirmDelete" @cancel="deleteModalOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "admin"] });

const { $api } = useNuxtApp();

const prompts = ref([]);
const typeFilter = ref("");
const modalOpen = ref(false);
const editingPrompt = ref(null);
const form = ref({ name: "", prompt: "", prompt_type: "rewrite" });
const formSnapshot = ref({});
const confirmClose = ref(false);
const message = ref("");
const msgType = ref("success");
const deleteModalOpen = ref(false);
const deletingPrompt = ref(null);

const filterOptions = [
  { label: "全部", value: "" },
  { label: "改写", value: "rewrite" },
  { label: "学习资料", value: "study" },
  { label: "试题", value: "exam" },
];

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const isFormDirty = computed(() => {
  const f = form.value;
  const s = formSnapshot.value;
  if (editingPrompt.value) {
    return f.name !== s.name || f.prompt !== s.prompt || f.prompt_type !== s.prompt_type;
  }
  return f.name !== "" || f.prompt !== "" || f.prompt_type !== "rewrite";
});

function typeLabel(t) {
  const map = { rewrite: "改写", study: "学习资料", exam: "试题" };
  return map[t] || t;
}

function typeBadge(t) {
  const map = { rewrite: "bg-amber-50 text-amber-700 border-amber-200", study: "bg-blue-50 text-blue-700 border-blue-200", exam: "bg-purple-50 text-purple-700 border-purple-200" };
  return map[t] || "bg-gray-50 text-gray-600 border-gray-200";
}

async function fetchPrompts() {
  try {
    const params = {};
    if (typeFilter.value) params.type = typeFilter.value;
    const res = await $api.get("/ai-prompts", { params });
    prompts.value = res.data.data;
  } catch {
    prompts.value = [];
  }
}

function openCreate() {
  editingPrompt.value = null;
  form.value = { name: "", prompt: "", prompt_type: "rewrite" };
  formSnapshot.value = { name: "", prompt: "", prompt_type: "rewrite" };
  confirmClose.value = false;
  modalOpen.value = true;
}

function openEdit(prompt) {
  editingPrompt.value = prompt;
  form.value = { name: prompt.name, prompt: prompt.prompt, prompt_type: prompt.prompt_type };
  formSnapshot.value = { name: prompt.name, prompt: prompt.prompt, prompt_type: prompt.prompt_type };
  confirmClose.value = false;
  modalOpen.value = true;
}

function closeModal() {
  if (isFormDirty.value) {
    confirmClose.value = true;
  } else {
    modalOpen.value = false;
  }
}

function forceClose() {
  confirmClose.value = false;
  modalOpen.value = false;
}

async function handleSubmit() {
  if (editingPrompt.value) {
    try {
      const res = await $api.put(`/ai-prompts/${editingPrompt.value.id}`, form.value);
      Object.assign(editingPrompt.value, res.data.data);
      showMessage("更新成功", "success");
      confirmClose.value = false;
      modalOpen.value = false;
    } catch (e) {
      showMessage(e.response?.data?.detail || "更新失败", "error");
    }
  } else {
    try {
      const res = await $api.post("/ai-prompts", form.value);
      prompts.value.push(res.data.data);
      showMessage("创建成功", "success");
      confirmClose.value = false;
      modalOpen.value = false;
    } catch (e) {
      showMessage(e.response?.data?.detail || "创建失败", "error");
    }
  }
}

function handleDelete(prompt) {
  deletingPrompt.value = prompt;
  deleteModalOpen.value = true;
}

async function confirmDelete() {
  const prompt = deletingPrompt.value;
  deleteModalOpen.value = false;
  try {
    await $api.delete(`/ai-prompts/${prompt.id}`);
    prompts.value = prompts.value.filter((p) => p.id !== prompt.id);
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

fetchPrompts();
</script>
