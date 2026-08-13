<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">{{ pageTitle }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ isTeacher ? '管理所有学员' : '管理系统中的所有用户' }}</p>
      </div>
      <button @click="openCreateModal" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 新增用户</button>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 mb-4 p-4">
      <div class="flex flex-wrap items-center gap-3">
        <input
          v-model="search"
          @input="onSearchInput"
          placeholder="搜索姓名 / 用户名 / 邮箱..."
          class="flex-1 min-w-[200px] px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
        <select v-if="!isTeacher" v-model="roleFilter" @change="fetchUsers" class="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
          <option value="">全部角色</option>
          <option value="admin">管理员</option>
          <option value="teacher">教师</option>
          <option value="student">学员</option>
        </select>
        <select v-model="statusFilter" @change="fetchUsers" class="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
          <option value="">全部状态</option>
          <option value="true">正常</option>
          <option value="false">禁用</option>
        </select>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th @click="toggleSort('id')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                ID {{ sortIcon('id') }}
              </th>
              <th @click="toggleSort('display_name')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                姓名 {{ sortIcon('display_name') }}
              </th>
              <th @click="toggleSort('username')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                用户名 {{ sortIcon('username') }}
              </th>
              <th @click="toggleSort('email')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                邮箱 {{ sortIcon('email') }}
              </th>
              <th @click="toggleSort('department')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                部门 {{ sortIcon('department') }}
              </th>
              <th @click="toggleSort('role')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                角色 {{ sortIcon('role') }}
              </th>
              <th class="px-4 py-3 font-medium">标签</th>
              <th @click="toggleSort('is_active')" class="px-4 py-3 font-medium cursor-pointer hover:text-gray-900 select-none">
                状态 {{ sortIcon('is_active') }}
              </th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 text-gray-500">{{ user.id }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">{{ user.display_name || user.username }}</td>
              <td class="px-4 py-3 text-gray-700">{{ user.username }}</td>
              <td class="px-4 py-3 text-gray-500">{{ user.email }}</td>
              <td class="px-4 py-3 text-gray-500">{{ user.department_name || '-' }}</td>
              <td class="px-4 py-3">
                <select
                  v-if="!isTeacher"
                  :value="user.role"
                  @change="handleRoleChange(user, $event)"
                  :disabled="user.id === authStore.user?.id"
                  class="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="admin">管理员</option>
                  <option value="teacher">教师</option>
                  <option value="student">学员</option>
                </select>
                <span v-else class="text-xs text-gray-600">学员</span>
              </td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1">
                  <span v-for="t in user.tags" :key="t" class="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded-full">{{ t }}</span>
                  <span v-if="!user.tags?.length" class="text-gray-400">-</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <button
                  @click="toggleStatus(user)"
                  :disabled="user.id === authStore.user?.id"
                  class="text-xs px-2 py-0.5 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
                  :class="user.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'"
                >{{ user.is_active ? '正常' : '禁用' }}</button>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button @click="openEditModal(user)" class="text-xs text-primary-600 hover:underline">编辑</button>
                  <button
                    v-if="user.id !== authStore.user?.id && user.role !== 'admin'"
                    @click="handleDelete(user)"
                    class="text-xs text-red-500 hover:underline"
                  >删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="users.length === 0 && !loading" class="px-4 py-12 text-center text-gray-400">暂无用户数据</div>

      <div class="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
        <span class="text-sm text-gray-500">共 {{ total }} 个用户</span>
        <div class="flex items-center gap-2">
          <button @click="page--; fetchUsers()" :disabled="page <= 1" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">上一页</button>
          <span class="text-sm text-gray-500">第 {{ page }} / {{ totalPages }} 页</span>
          <button @click="page++; fetchUsers()" :disabled="page >= totalPages" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">下一页</button>
        </div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <!-- Edit Modal -->
    <div v-if="editModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEditModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">编辑用户</h3>
        <form @submit.prevent="handleEditSubmit" class="space-y-3">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">展示名</label><input v-model="editForm.display_name" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">用户名</label><input v-model="editForm.username" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label><input v-model="editForm.email" type="email" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">手机</label><input v-model="editForm.phone" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">部门</label>
            <select v-model="editForm.department_id" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
              <option :value="null">无</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div v-if="!isTeacher">
            <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select v-model="editForm.role" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
              <option value="student">学员</option>
              <option value="teacher">教师</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label class="text-sm font-medium text-gray-700">激活</label>
            <input type="checkbox" v-model="editForm.is_active" class="rounded" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">标签</label>
            <div class="max-h-40 overflow-y-auto space-y-1 border border-gray-100 rounded-lg p-2">
              <label v-for="t in allTags" :key="t.id" class="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 px-1 py-0.5 rounded">
                <input type="checkbox" :checked="editTagIds.includes(t.id)" @change="toggleTag(t.id)" class="rounded" />
                {{ t.name }}
              </label>
              <div v-if="allTags.length === 0" class="text-xs text-gray-400">暂无标签</div>
            </div>
            <div class="flex gap-1 mt-1">
              <input v-model="editNewTagName" placeholder="新建标签名称" class="flex-1 px-2 py-1 text-xs border border-gray-200 rounded-lg" @keyup.enter="handleCreateTag" />
              <button type="button" @click="handleCreateTag" class="px-3 py-1 bg-primary-600 text-white text-xs rounded-lg hover:bg-primary-700">新建</button>
            </div>
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button>
            <button type="button" @click="closeEditModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
          </div>
        </form>
        <div class="mt-3 pt-3 border-t border-gray-100">
          <button @click="handleResetPassword" class="text-sm text-accent-600 hover:underline">重置密码</button>
          <input v-model="editForm.new_password" placeholder="新密码" class="ml-2 px-2 py-1 text-xs border border-gray-200 rounded-lg w-32" />
        </div>
      </div>
    </div>

    <!-- Edit Confirm Close Dialog -->
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

    <!-- Create Modal -->
    <div v-if="createModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeCreateModal">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-bold text-gray-900 mb-4">新增用户</h3>
        <form @submit.prevent="handleCreateSubmit" class="space-y-3">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">展示名</label><input v-model="createForm.display_name" placeholder="可选" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">用户名 <span class="text-red-500">*</span></label><input v-model="createForm.username" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">邮箱 <span class="text-red-500">*</span></label><input v-model="createForm.email" type="email" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">手机 <span class="text-red-500">*</span></label><input v-model="createForm.phone" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">部门</label>
            <select v-model="createForm.department_id" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
              <option :value="null">无</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div v-if="!isTeacher">
            <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select v-model="createForm.role" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
              <option value="student">学员</option>
              <option value="teacher">教师</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">密码 <span class="text-red-500">*</span></label><input v-model="createForm.password" type="password" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" /></div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">创建</button>
            <button type="button" @click="closeCreateModal" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">取消</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Create Confirm Close Dialog -->
    <div v-if="createConfirmClose" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">放弃填写？</h3>
        <p class="text-sm text-gray-500 mb-4">已输入的内容将丢失。</p>
        <div class="flex gap-3">
          <button @click="forceCloseCreate" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button>
          <button @click="createConfirmClose = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续填写</button>
        </div>
      </div>
    </div>

    <ConfirmModal :show="deleteModalOpen" title="删除用户" :message="`确定删除用户「${deletingUser?.display_name || deletingUser?.username}」？`" variant="danger" @confirm="doDelete" @cancel="closeDeleteModal" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const authStore = useAuthStore();
const { $api } = useNuxtApp();

const users = ref([]);
const departments = ref([]);
const allTags = ref([]);
const total = ref(0);
const deleteModalOpen = ref(false);
const deletingUser = ref(null);
const page = ref(1);
const pageSize = 20;
const loading = ref(false);
const message = ref("");
const msgType = ref("success");
const search = ref("");
const roleFilter = ref("");
const statusFilter = ref("");
const sortBy = ref("id");
const sortOrder = ref("asc");
const editModalOpen = ref(false);
const createModalOpen = ref(false);
const editConfirmClose = ref(false);
const createConfirmClose = ref(false);
const editingUser = ref(null);
const editForm = ref({});
const editFormSnapshot = ref({});
const editTagIds = ref([]);
const editNewTagName = ref("");
const createForm = ref({ username: "", display_name: "", email: "", phone: "", department_id: null, role: "student", password: "" });

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1);
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");
const isTeacher = computed(() => authStore.user?.role === "teacher");
const pageTitle = computed(() => isTeacher.value ? "学员管理" : "人员管理");

const isEditDirty = computed(() => {
  const f = editForm.value;
  const s = editFormSnapshot.value;
  return f.display_name !== (s.display_name || "")
    || f.username !== s.username
    || f.email !== s.email
    || f.phone !== (s.phone || "")
    || (f.department_id || null) !== (s.department_id || null)
    || f.role !== s.role
    || f.is_active !== s.is_active
    || editTagIds.value.sort().join(",") !== (s.tagIds || []).sort().join(",")
    || editNewTagName.value !== (s.newTagName || "");
});

const isCreateDirty = computed(() => {
  return createForm.value.username || createForm.value.display_name
    || createForm.value.email || createForm.value.phone
    || createForm.value.password;
});

let searchTimer = null;

function sortIcon(field) {
  if (sortBy.value !== field) return "";
  return sortOrder.value === "asc" ? "\u25B2" : "\u25BC";
}

function toggleSort(field) {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    sortBy.value = field;
    sortOrder.value = "asc";
  }
  fetchUsers();
}

function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { page.value = 1; fetchUsers(); }, 300);
}

async function fetchUsers() {
  loading.value = true;
  try {
    const params = { page: page.value, page_size: pageSize, sort_by: sortBy.value, order: sortOrder.value };
    if (search.value) params.search = search.value;
    if (roleFilter.value) params.role = roleFilter.value;
    if (statusFilter.value) params.is_active = statusFilter.value;
    const res = await $api.get("/users", { params });
    users.value = res.data.data.items;
    total.value = res.data.data.total;
  } catch (e) {
    showMessage("获取用户列表失败", "error");
  } finally {
    loading.value = false;
  }
}

async function fetchDepartments() {
  try {
    const res = await $api.get("/departments");
    departments.value = res.data.data;
  } catch {}
}

async function fetchAllTags() {
  try {
    const res = await $api.get("/tags");
    allTags.value = res.data.data;
  } catch {}
}

async function handleRoleChange(user, event) {
  const newRole = event.target.value;
  try {
    await $api.patch(`/users/${user.id}/role`, { role: newRole });
    user.role = newRole;
    showMessage("角色更新成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "更新失败", "error");
    event.target.value = user.role;
  }
}

async function toggleStatus(user) {
  const newStatus = !user.is_active;
  try {
    await $api.patch(`/users/${user.id}`, { is_active: newStatus });
    user.is_active = newStatus;
    showMessage("状态更新成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "更新失败", "error");
  }
}

function openEditModal(user) {
  editingUser.value = user;
  editForm.value = {
    username: user.username,
    display_name: user.display_name || "",
    email: user.email,
    phone: user.phone,
    department_id: user.department_id,
    role: user.role,
    is_active: user.is_active,
    new_password: "",
  };
  editNewTagName.value = "";
  editConfirmClose.value = false;
  editModalOpen.value = true;
  editTagIds.value = [];
  $api.get(`/users/${user.id}/tags`).then(r => { editTagIds.value = (r.data.data || []).map(t => t.id); }).catch(() => {});
  editFormSnapshot.value = {
    display_name: user.display_name || "",
    username: user.username,
    email: user.email,
    phone: user.phone || "",
    department_id: user.department_id || null,
    role: user.role,
    is_active: user.is_active,
    tagIds: [],
    newTagName: "",
  };
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
    const body = {
      username: editForm.value.username,
      display_name: editForm.value.display_name || null,
      email: editForm.value.email,
      phone: editForm.value.phone,
      department_id: editForm.value.department_id,
      role: editForm.value.role,
      is_active: editForm.value.is_active,
    };
    const res = await $api.patch(`/users/${editingUser.value.id}`, body);
    Object.assign(editingUser.value, res.data.data);
    await $api.put(`/users/${editingUser.value.id}/tags`, { tag_ids: editTagIds.value });
    editModalOpen.value = false;
    showMessage("保存成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "保存失败", "error");
  }
}

async function handleResetPassword() {
  if (!editForm.value.new_password) { showMessage("请输入新密码", "error"); return; }
  try {
    await $api.patch(`/users/${editingUser.value.id}/password`, { password: editForm.value.new_password });
    showMessage("密码已重置", "success");
    editForm.value.new_password = "";
  } catch (e) {
    showMessage(e.response?.data?.detail || "重置失败", "error");
  }
}

function toggleTag(tagId) {
  const idx = editTagIds.value.indexOf(tagId);
  if (idx >= 0) editTagIds.value.splice(idx, 1);
  else editTagIds.value.push(tagId);
}

async function handleCreateTag() {
  if (!editNewTagName.value) return;
  try {
    const r = await $api.post("/tags", { name: editNewTagName.value });
    allTags.value.push(r.data.data);
    editTagIds.value.push(r.data.data.id);
    editNewTagName.value = "";
    showMessage("标签已创建", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "创建标签失败", "error");
  }
}

function openCreateModal() {
  createForm.value = { username: "", display_name: "", email: "", phone: "", department_id: null, role: "student", password: "" };
  createConfirmClose.value = false;
  createModalOpen.value = true;
}

function closeCreateModal() {
  if (isCreateDirty.value) {
    createConfirmClose.value = true;
  } else {
    createModalOpen.value = false;
  }
}

function forceCloseCreate() {
  createConfirmClose.value = false;
  createModalOpen.value = false;
}

async function handleCreateSubmit() {
  try {
    await $api.post("/users", createForm.value);
    createModalOpen.value = false;
    showMessage("用户创建成功", "success");
    fetchUsers();
  } catch (e) {
    showMessage(e.response?.data?.detail || "创建失败", "error");
  }
}

function handleDelete(user) {
  deletingUser.value = user;
  deleteModalOpen.value = true;
}

async function doDelete() {
  deleteModalOpen.value = false;
  const user = deletingUser.value;
  try {
    await $api.delete(`/users/${user.id}`);
    users.value = users.value.filter((u) => u.id !== user.id);
    total.value--;
    showMessage("已删除", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "删除失败", "error");
  }
}

function closeDeleteModal() {
  deleteModalOpen.value = false;
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

fetchDepartments();
fetchAllTags();
fetchUsers();
</script>
