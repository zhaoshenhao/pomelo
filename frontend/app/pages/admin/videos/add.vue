<template>
  <div>
    <div class="mb-4"><NuxtLink to="/admin/videos" class="text-sm text-primary-600 hover:underline">&larr; 返回视频列表</NuxtLink></div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">新增视频</h2>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-lg">
      <div class="space-y-4">
        <div><label class="block text-sm font-medium text-gray-700 mb-1">来源</label>
          <div class="flex gap-4"><label class="flex items-center gap-1"><input type="radio" v-model="source" value="local" class="rounded" /><span class="text-sm">本地文件</span></label><label class="flex items-center gap-1"><input type="radio" v-model="source" value="oss" class="rounded" /><span class="text-sm">OSS</span></label></div>
        </div>

        <template v-if="source === 'local'">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">选择文件</label><input type="file" ref="fileInput" accept="video/*" @change="onFileChange" class="w-full text-sm" /></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">OSS 目标</label>
            <div class="flex gap-4 mb-2"><label class="flex items-center gap-1"><input type="radio" v-model="ossDest" value="existing" class="rounded" /><span class="text-sm">选择已有目录</span></label><label class="flex items-center gap-1"><input type="radio" v-model="ossDest" value="new" class="rounded" /><span class="text-sm">输入新路径</span></label></div>
            <div v-if="ossDest === 'existing'" class="flex items-center gap-2">
              <select v-model="ossDir" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"><option value="">请选择...</option><option v-for="d in ossDirs" :key="d" :value="d">{{ d }}</option></select>
              <button type="button" @click="loadOssDirs" title="刷新目录" class="px-2.5 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm shrink-0">&#x1F504;</button>
            </div>
            <input v-else v-model="ossNewPath" placeholder="输入新路径（如 myfolder/sub）" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" />
          </div>
        </template>

        <template v-else>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">选择 OSS 文件</label><input v-model="ossSearch" @input="loadOssObjects" placeholder="搜索..." class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg mb-2" />
            <div class="flex items-start gap-2">
              <select v-model="ossSelected" size="6" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"><option v-for="o in ossObjects" :key="o.key" :value="o.key">{{ o.name }} ({{ fmtSize(o.size) }})</option></select>
              <button type="button" @click="loadOssObjects" title="刷新文件" class="px-2.5 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm shrink-0">&#x1F504;</button>
            </div>
          </div>
        </template>

        <div><label class="block text-sm font-medium text-gray-700 mb-1">名称</label><input v-model="form.name" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
        <div><label class="block text-sm font-medium text-gray-700 mb-1">描述</label><textarea v-model="form.description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea></div>
        <div><label class="block text-sm font-medium text-gray-700 mb-1">文档库</label>
          <div class="flex items-center gap-2">
            <select v-model="form.library_id" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"><option :value="null">无（不关联文档库）</option><option v-for="l in libraries" :key="l.id" :value="l.id">{{ l.name }}</option></select>
            <button type="button" @click="fetchLibraries" title="刷新文档库" class="px-2.5 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm shrink-0">&#x1F504;</button>
          </div>
        </div>
        <div><label class="flex items-center gap-2"><input type="checkbox" v-model="form.active" class="rounded" /><span class="text-sm text-gray-700">激活（默认是）</span></label></div>

        <button @click="doCreate" :disabled="!canCreate || creating" class="w-full py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">{{ creating ? '创建中...' : '确认创建' }}</button>
      </div>

      <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
    </div>

    <div v-if="creating" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">{{ creatingText }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const router = useRouter();

const source = ref("local");
const fileInput = ref(null); const file = ref(null);
const ossDest = ref("existing"); const ossDir = ref(""); const ossNewPath = ref("");
const ossDirs = ref([]); const ossObjects = ref([]); const ossSearch = ref(""); const ossSelected = ref("");
const form = ref({ name: "", description: "", library_id: null, active: true });
const libraries = ref([]);
const creating = ref(false); const message = ref(""); const msgType = ref("success");
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const canCreate = computed(() => form.value.name.trim() && (source.value === "oss" ? ossSelected.value : file.value));
const creatingText = computed(() => source.value === "local" ? "正在上传并创建视频，请稍候..." : "正在创建视频，请稍候...");

function fmtSize(b) { if (!b) return ""; return b > 1048576 ? (b/1048576).toFixed(1)+"MB" : b > 1024 ? Math.round(b/1024)+"KB" : b+"B"; }

function onFileChange(e) { file.value = e.target.files?.[0] || null; if (file.value) { form.value.name = form.value.name || file.value.name.replace(/\.[^.]+$/, ""); } }

async function loadOssDirs() { try { const r = await $api.get("/videos/oss/dirs"); ossDirs.value = r.data.data; } catch {} }
async function loadOssObjects() { try { const r = await $api.get("/videos/oss/objects", { params: { prefix: ossSearch.value } }); ossObjects.value = r.data.data; } catch {} }

async function doCreate() {
  if (source.value === "local") {
    if (!file.value) { showMessage("请先选择文件", "error"); return; }
    const path = (ossDest.value === "existing" ? ossDir.value : ossNewPath.value).trim();
    if (!path) { showMessage("请选择或输入OSS目录", "error"); return; }
  }
  if (source.value === "oss" && !ossSelected.value) { showMessage("请选择OSS文件", "error"); return; }
  creating.value = true;
  try {
    if (source.value === "local") {
      const fd = new FormData(); fd.append("file", file.value);
      const path = (ossDest.value === "existing" ? ossDir.value : ossNewPath.value).trim();
      const qp = { name: form.value.name, description: form.value.description, active: form.value.active, oss_dir: path };
      if (form.value.library_id) qp.library_id = form.value.library_id;
      const r = await $api.post("/videos/upload", fd, { params: qp, headers: { "Content-Type": "multipart/form-data" } });
      showMessage(`上传成功，时长 ${fmtDur(r.data.data.duration_seconds)}`, "success");
    } else {
      await $api.post("/videos/from-oss", { name: form.value.name, description: form.value.description, library_id: form.value.library_id, active: form.value.active, oss_path: ossSelected.value });
      showMessage("创建成功", "success");
    }
    setTimeout(() => router.push("/admin/videos"), 800);
  } catch (e) { showMessage(e.response?.data?.detail || "创建失败", "error"); } finally { creating.value = false; }
}

function fmtDur(s) { if (!s) return "0:00"; const m = Math.floor(s/60); const r = s%60; return `${m}:${String(r).padStart(2,"0")}`; }
function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }

async function fetchLibraries() { try { const r = await $api.get("/libraries"); libraries.value = r.data.data; } catch {} }

loadOssDirs(); loadOssObjects(); fetchLibraries();
</script>
