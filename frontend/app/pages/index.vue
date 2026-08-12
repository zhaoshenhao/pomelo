<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-bold text-gray-900">工作台</h2>
      <p class="text-sm text-gray-500 mt-1">欢迎回来，{{ authStore.user?.username }}</p>
    </div>

    <div v-if="loading" class="px-4 py-12 text-center text-gray-400 text-sm">加载中...</div>

    <!-- ============ 教师/管理员工作台 ============ -->
    <template v-else-if="authStore.isTeacherOrAdmin && teacherData">
      <section class="mb-8">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">管理模块</h3>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <NuxtLink to="/admin/libraries" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition block">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4C4;</span><h4 class="font-semibold text-sm">文档管理</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-500 mb-3">上传和管理学习文档资料</p>
              <div class="text-sm text-gray-500">文档数：<span class="font-bold text-gray-900">{{ teacherData.counts.documents }}</span></div>
            </div>
          </NuxtLink>
          <NuxtLink to="/admin/users" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition block">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F465;</span><h4 class="font-semibold text-sm">人员管理</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-500 mb-3">管理系统用户与角色</p>
              <div class="text-sm text-gray-500">学生 <span class="font-bold text-gray-900">{{ teacherData.counts.students }}</span> / 老师 <span class="font-bold text-gray-900">{{ teacherData.counts.teachers }}</span> / 管理员 <span class="font-bold text-gray-900">{{ teacherData.counts.admins }}</span></div>
            </div>
          </NuxtLink>
          <NuxtLink to="/admin/departments" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition block">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F3E2;</span><h4 class="font-semibold text-sm">部门管理</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-500 mb-3">管理组织部门</p>
              <div class="text-sm text-gray-500">部门数：<span class="font-bold text-gray-900">{{ teacherData.counts.departments }}</span></div>
            </div>
          </NuxtLink>
          <NuxtLink to="/admin/question-banks" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition block">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4DA;</span><h4 class="font-semibold text-sm">题库管理</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-500 mb-3">生成和管理试题题库</p>
              <div class="text-sm text-gray-500">题库数：<span class="font-bold text-gray-900">{{ teacherData.counts.question_banks }}</span></div>
            </div>
          </NuxtLink>
          <NuxtLink to="/admin/study-materials" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition block">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4D6;</span><h4 class="font-semibold text-sm">学习资料</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-500 mb-3">生成和管理学习材料</p>
              <div class="text-sm text-gray-500">资料数：<span class="font-bold text-gray-900">{{ teacherData.counts.study_materials }}</span></div>
            </div>
          </NuxtLink>
          <NuxtLink to="/admin/exams" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition block">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4DD;</span><h4 class="font-semibold text-sm">试卷管理</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-500 mb-3">创建和管理考试试卷</p>
              <div class="text-sm text-gray-500">试卷数：<span class="font-bold text-gray-900">{{ teacherData.counts.exams }}</span></div>
            </div>
          </NuxtLink>
        </div>
      </section>

      <section class="mb-8" v-if="teacherData.recent_exams.length">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">最近的考试安排</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="e in teacherData.recent_exams" :key="e.batch_id" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4CB;</span><h4 class="font-semibold text-sm truncate">{{ e.name }}</h4></div>
            <div class="p-4">
              <div class="text-xs text-gray-500 space-y-1 mb-3">
                <div v-if="e.start_time || e.end_time">时间：{{ fmtTs(e.start_time) || '-' }} ~ {{ fmtTs(e.end_time) || '-' }}</div>
                <div>时长 {{ e.duration_minutes }} 分钟 · 及格 {{ e.pass_score }} 分</div>
                <div>题目：{{ e.question_count }} 题（{{ fmtTypeCounts(e.type_counts) }}）</div>
                <div>总人数：{{ e.arranged_count }}</div>
              </div>
              <div v-if="e.started || e.ended" class="text-xs space-y-1 border-t border-gray-100 pt-3">
                <div><span class="text-gray-500">完成：</span>{{ e.completed_count }}<span class="text-gray-500 ml-3">平均分：</span>{{ e.average_score !== null ? e.average_score : '-' }}<span class="text-gray-500 ml-3">及格率：</span>{{ e.pass_rate !== null ? e.pass_rate + '%' : '-' }}</div>
                <div><span :class="e.ended ? 'text-red-500' : 'text-green-600'" class="font-medium">{{ e.ended ? '已结束' : '进行中' }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="teacherData.study_progress.length">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">学习进度情况</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="m in teacherData.study_progress" :key="m.material_id" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4CA;</span><h4 class="font-semibold text-sm truncate">{{ m.name }}</h4></div>
            <div class="p-4">
              <div class="text-xs text-gray-500 space-y-1">
                <div>要求阅读：{{ m.min_minutes }} 分钟</div>
                <div>已开始：{{ m.started_count }} 人（未完成 {{ m.started_count - m.completed_count }}）</div>
                <div>已完成：{{ m.completed_count }} 人</div>
                <div>总学习时间：{{ fmtSeconds(m.total_study_seconds) }}</div>
                <div>人均学习：{{ fmtSeconds(m.avg_study_seconds) }} · 人均阅读 {{ m.avg_read_count }} 次</div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- ============ 学生工作台 ============ -->
    <template v-else-if="!authStore.isTeacherOrAdmin && studentData">
      <section class="mb-8">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">我的考试</h3>
        <div v-if="studentData.exams.length === 0" class="text-sm text-gray-400">暂无考试</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="e in studentData.exams" :key="e.assignment_id || e.exam_id" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition cursor-pointer" @click="goExam(e)">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4DD;</span><h4 class="font-semibold text-sm truncate">{{ e.name }}</h4></div>
            <div class="p-4">
              <div class="text-xs text-gray-500 space-y-1 mb-3">
                <div v-if="e.start_time || e.end_time">时间：{{ fmtTs(e.start_time) || '-' }} ~ {{ fmtTs(e.end_time) || '-' }}</div>
                <div>时长 {{ e.duration_minutes }} 分钟 · 及格 {{ e.pass_score }} 分</div>
                <div>题目：{{ e.question_count }} 题（{{ fmtTypeCounts(e.type_counts) }}）</div>
              </div>
              <div class="border-t border-gray-100 pt-3">
                <template v-if="e.status === 'completed'">
                  <div class="text-xs"><span class="text-accent-600 font-bold">得分：{{ e.score }}</span><span class="ml-3" :class="e.passed ? 'text-green-600' : 'text-red-500'">{{ e.passed ? '已通过' : '未通过' }}</span></div>
                </template>
                <span v-else class="text-xs px-2 py-0.5 rounded" :class="e.status === 'assigned' ? 'bg-amber-100 text-amber-700' : 'bg-primary-100 text-primary-700'">{{ e.start_time && new Date(e.start_time) > new Date() ? '即将开始' : '进行中' }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="mb-8">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">我的学习课程</h3>
        <div v-if="studentData.courses.length === 0" class="text-sm text-gray-400">暂无课程</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="c in studentData.courses" :key="c.material_id" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition cursor-pointer" @click="goRead(c.material_id)">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F4D6;</span><h4 class="font-semibold text-sm truncate">{{ c.material_name }}</h4></div>
            <div class="p-4">
              <p class="text-xs text-gray-400 mb-2 truncate">{{ c.material_description || '暂无描述' }}</p>
              <div class="text-xs text-gray-500 space-y-1">
                <div>最少阅读：{{ c.min_minutes }} 分钟</div>
                <div class="flex gap-2"><span :class="c.has_started ? 'text-green-600' : 'text-gray-400'">{{ c.has_started ? '已阅读' : '未阅读' }}</span><span :class="c.completed ? 'text-green-600' : 'text-gray-400'">{{ c.completed ? '已完成' : '未完成' }}</span><span v-if="c.has_started" class="text-gray-500">已学 {{ fmtSeconds(c.total_study_seconds) }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h3 class="text-lg font-semibold text-gray-800 mb-3">我的模拟训练</h3>
        <div v-if="studentData.drills.length === 0" class="text-sm text-gray-400">暂无可用题库</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="d in studentData.drills" :key="d.id" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition cursor-pointer" @click="goDrill(d.id)">
            <div class="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-950 text-white flex items-center gap-2"><span class="text-base">&#x1F3AF;</span><h4 class="font-semibold text-sm truncate">{{ d.name }}</h4></div>
            <div class="p-4">
              <div class="text-xs text-gray-500 space-y-1 mb-3">
                <div>题目：{{ d.question_count }} 题（{{ fmtTypeCounts(d.type_counts) }}）</div>
              </div>
              <div class="border-t border-gray-100 pt-3">
                <div v-if="d.total_answered > 0" class="text-xs text-gray-500 space-x-2">
                  <span>已答 {{ d.total_answered }} 题</span><span class="text-gray-300">·</span><span>正确率 {{ d.accuracy }}%</span><span class="text-gray-300">·</span><span>曾答对 {{ d.ever_correct_questions }} 题</span>
                </div>
                <span v-else class="text-xs text-gray-400">尚未训练</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: "auth" });

const { $api } = useNuxtApp();
const authStore = useAuthStore();
const router = useRouter();

const loading = ref(true);
const teacherData = ref(null);
const studentData = ref(null);

const TYPE_NAMES = { single: "单选", multiple: "多选", true_false: "判断", fill: "填空", match: "匹配" };

function fmtTypeCounts(tc) {
  if (!tc || Object.keys(tc).length === 0) return "暂无";
  return Object.entries(tc).map(([k, v]) => `${TYPE_NAMES[k] || k}${v}`).join(" ");
}

function fmtTs(t) {
  if (!t) return "";
  return t.substring(0, 16).replace("T", " ");
}

function fmtSeconds(sec) {
  if (!sec || sec <= 0) return "< 1 分钟";
  const m = Math.floor(sec / 60);
  if (m < 1) return Math.round(sec) + " 秒";
  if (m < 60) return m + " 分钟";
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return h + " 小时 " + rm + " 分";
}

function goExam(e) {
  if (e.status === "completed") {
    router.push(`/student/exams/${e.exam_id}/view`);
  } else {
    router.push("/student/exams");
  }
}

function goRead(materialId) {
  window.open(`/student/courses/read/${materialId}`, "_blank", "width=1050,height=750");
}

function goDrill(qbId) {
  window.open(`/student/training/${qbId}`, "_blank", "width=1000,height=700");
}

async function fetchDashboard() {
  loading.value = true;
  try {
    if (authStore.isTeacherOrAdmin) {
      const r = await $api.get("/dashboard/teacher");
      teacherData.value = r.data.data;
    } else {
      const r = await $api.get("/dashboard/student");
      studentData.value = r.data.data;
    }
  } catch {} finally {
    loading.value = false;
  }
}

fetchDashboard();
</script>
