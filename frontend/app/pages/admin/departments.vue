<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-bold text-gray-900">部门管理</h2>
      <p class="text-sm text-gray-500 mt-1">管理部门列表</p>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-gray-600">
          <tr>
            <th class="px-4 py-3 font-medium">ID</th>
            <th class="px-4 py-3 font-medium">部门名称</th>
            <th class="px-4 py-3 font-medium">用户数</th>
            <th class="px-4 py-3 font-medium">创建时间</th>
            <th class="px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="dept in departments" :key="dept.id" class="hover:bg-gray-50 transition">
            <td class="px-4 py-3 text-gray-500">{{ dept.id }}</td>
            <td class="px-4 py-3">
              <div v-if="editingId === dept.id" class="flex items-center gap-2">
                <input
                  v-model="editName"
                  @keyup.enter="handleUpdate(dept.id)"
                  @keyup.escape="cancelEdit"
                  class="px-2 py-1 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 w-40"
                />
                <button @click="handleUpdate(dept.id)" class="text-xs text-primary-600 hover:underline">保存</button>
                <button @click="cancelEdit" class="text-xs text-gray-400 hover:underline">取消</button>
              </div>
              <span v-else class="font-medium text-gray-900">{{ dept.name }}</span>
            </td>
            <td class="px-4 py-3 text-gray-500">{{ dept.user_count }}</td>
            <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(dept.created_at) }}</td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <button v-if="editingId !== dept.id" @click="startEdit(dept)" class="text-xs text-primary-600 hover:underline">编辑</button>
                <button @click="handleDelete(dept)" :disabled="dept.user_count > 0" class="text-xs text-red-500 hover:underline disabled:opacity-30 disabled:cursor-not-allowed">删除</button>
              </div>
            </td>
          </tr>
          <tr class="bg-gray-50">
            <td class="px-4 py-3 text-gray-400">#</td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <input
                  v-model="newName"
                  @keyup.enter="handleCreate"
                  placeholder="新部门名称"
                  class="px-2 py-1 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 w-40"
                />
                <button @click="handleCreate" :disabled="!newName.trim()" class="px-2 py-1 text-xs bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed">添加</button>
              </div>
            </td>
            <td class="px-4 py-3"></td>
            <td class="px-4 py-3"></td>
            <td class="px-4 py-3"></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <ConfirmModal :show="deleteModalOpen" title="删除部门" :message="`确定删除部门「${deletingDept?.name}」？`" variant="danger" @confirm="doDelete" @cancel="closeDeleteModal" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "admin"] });

const authStore = useAuthStore();
const { $api } = useNuxtApp();

const departments = ref([]);
const newName = ref("");
const editingId = ref(null);
const editName = ref("");
const message = ref("");
const msgType = ref("success");
const deleteModalOpen = ref(false);
const deletingDept = ref(null);

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

async function fetchDepartments() {
  try {
    const res = await $api.get("/departments");
    departments.value = res.data.data;
  } catch {}
}

async function handleCreate() {
  if (!newName.value.trim()) return;
  try {
    const res = await $api.post("/departments", { name: newName.value.trim() });
    departments.value.push(res.data.data);
    newName.value = "";
    showMessage("添加成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "添加失败", "error");
  }
}

function startEdit(dept) {
  editingId.value = dept.id;
  editName.value = dept.name;
}

function cancelEdit() {
  editingId.value = null;
  editName.value = "";
}

async function handleUpdate(deptId) {
  if (!editName.value.trim()) return;
  try {
    const res = await $api.patch(`/departments/${deptId}`, { name: editName.value.trim() });
    const idx = departments.value.findIndex((d) => d.id === deptId);
    if (idx !== -1) departments.value[idx] = res.data.data;
    editingId.value = null;
    showMessage("更新成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "更新失败", "error");
  }
}

function handleDelete(dept) {
  if (dept.user_count > 0) return;
  deletingDept.value = dept;
  deleteModalOpen.value = true;
}

async function doDelete() {
  deleteModalOpen.value = false;
  const dept = deletingDept.value;
  try {
    await $api.delete(`/departments/${dept.id}`);
    departments.value = departments.value.filter((d) => d.id !== dept.id);
    showMessage("已删除", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "删除失败", "error");
  }
}

function closeDeleteModal() {
  deleteModalOpen.value = false;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  return dateStr.substring(0, 10);
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

fetchDepartments();
</script>
