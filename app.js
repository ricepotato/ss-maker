let viewMode = "grid";
let filterKind = "all"; // 'all' | 'video' | 'image'
let navStack = [];
let currentNode = videos; // videos is the tree root node
let viewerMode = "fit"; // 'fit' | 'original'
let hasDragged = false;

// standalone 모드: 폴더마다 생성된 index.html 에 해당 폴더 데이터만 인라인되어 있음
const STANDALONE = videos.standalone === true;

// standalone 모드에서는 경로가 index.html 기준 상대경로이므로 URL 인코딩
function toUrl(path) {
  if (!STANDALONE) return path;
  return path.split("/").map(encodeURIComponent).join("/");
}

// PotPlayer 는 절대경로가 필요하므로 상대경로를 현재 페이지 위치 기준으로 변환
function toPotPath(path) {
  if (!STANDALONE) return path.replace(/\\/gi, "/");
  const url = new URL(toUrl(path), location.href);
  return decodeURIComponent(url.pathname).replace(/^\/([A-Za-z]:)/, "$1");
}

function renderApp() {
  const appEl = document.getElementById("app");
  appEl.innerHTML = "";

  const ul = document.createElement("ul");
  ul.className = viewMode === "grid" ? "list-view grid-view" : "list-view";

  const dirs = currentNode.children.filter((c) => c.type === "dir");
  const files = currentNode.children.filter((c) => {
    if (c.type !== "file") return false;
    if (filterKind === "all") return true;
    return c.kind === filterKind;
  });

  dirs.forEach((dir) => {
    const li = document.createElement("li");
    li.className = "list-item list-item--dir";
    const count = countFiles(dir);
    let previews = collectPreviews(dir, DIR_PREVIEW_COUNT);
    // 4~5개는 2x2로 맞추기 위해 4개만 사용
    if (previews.length === 5) previews = previews.slice(0, 4);
    const mosaic = previews.length
      ? `<div class="dir-mosaic dir-mosaic--${previews.length}">${previews
          .map((src) => `<img src='${toUrl(src)}' loading='lazy'/>`)
          .join("")}</div>`
      : `<div class="dir-mosaic dir-mosaic--empty"><span class="list-item__dir-icon">&#128193;</span></div>`;
    li.innerHTML = `
      <div class="list-item__container">
        <div class="list-item__image_container">${mosaic}</div>
        <div class="list-item__info">
          <div class="list-item__name">&#128193; ${dir.name}</div>
          <div class="list-item__dir-count">${count}개 파일</div>
        </div>
      </div>`;
    li.addEventListener("click", () => {
      if (STANDALONE) {
        location.href = encodeURIComponent(dir.name) + "/index.html";
        return;
      }
      navigateTo(dir, [...navStack, currentNode]);
    });
    ul.appendChild(li);
  });

  files.forEach((file) => {
    const li = document.createElement("li");
    li.className = "list-item";
    if (file.kind === "image") {
      li.classList.add("list-item--image");
      new ImageItem({ target: li, initialState: file });
    } else {
      new ListItem({ target: li, initialState: file });
    }
    ul.appendChild(li);
  });

  appEl.appendChild(ul);
}

function countFiles(node) {
  if (node.count !== undefined) return node.count;
  let count = 0;
  for (const child of node.children) {
    if (child.type === "file") count++;
    else count += countFiles(child);
  }
  return count;
}

const DIR_PREVIEW_COUNT = 6;

// 폴더 내부 항목의 미리보기 이미지를 너비 우선으로 수집
function collectPreviews(node, limit) {
  if (node.previews) return node.previews.slice(0, limit);
  const result = [];
  const queue = [node];
  while (queue.length && result.length < limit) {
    const cur = queue.shift();
    for (const child of cur.children) {
      if (result.length >= limit) break;
      if (child.type === "dir") {
        queue.push(child);
      } else if (child.kind === "image") {
        result.push(child.thumbnail || child.target);
      } else if (child.snapshots && child.snapshots.length) {
        result.push(child.snapshots[0]);
      }
    }
  }
  return result;
}

function updateNav() {
  const btnBack = document.getElementById("btnBack");
  const breadcrumb = document.getElementById("breadcrumb");
  if (STANDALONE) {
    const crumbs = videos.crumbs || [videos.name];
    btnBack.disabled = crumbs.length <= 1;
    breadcrumb.innerHTML = "";
    crumbs.forEach((name, i) => {
      if (i > 0) breadcrumb.appendChild(document.createTextNode(" / "));
      const depth = crumbs.length - 1 - i;
      if (depth === 0) {
        breadcrumb.appendChild(document.createTextNode(name));
        return;
      }
      const a = document.createElement("a");
      a.href = "../".repeat(depth) + "index.html";
      a.textContent = name;
      breadcrumb.appendChild(a);
    });
    return;
  }
  btnBack.disabled = navStack.length === 0;
  const parts = navStack.map((n) => n.name).concat(currentNode.name);
  breadcrumb.textContent = parts.join(" / ");
}

function getNodePath(node, stack) {
  return [...stack.map((n) => n.name), node.name]
    .map(encodeURIComponent)
    .join("/");
}

function findNodeByPath(pathStr) {
  if (!pathStr) return { node: videos, stack: [] };
  const parts = pathStr.split("/").map((s) => decodeURIComponent(s));
  if (parts[0] !== videos.name) return null;
  let node = videos;
  const stack = [];
  for (let i = 1; i < parts.length; i++) {
    const next = node.children.find(
      (c) => c.type === "dir" && c.name === parts[i],
    );
    if (!next) return null;
    stack.push(node);
    node = next;
  }
  return { node, stack };
}

function navigateTo(node, stack, addHistory = true) {
  navStack = stack;
  currentNode = node;
  if (addHistory) {
    const path = getNodePath(node, stack);
    history.pushState({ path }, "", "#" + path);
  }
  updateNav();
  renderApp();
  window.scrollTo(0, 0);
}

function ListItem({ target, initialState }) {
  this.state = { ...initialState };
  this.currentIndex = 0;
  const render = () => {
    target.innerHTML = `
    <div class="list-item__container">
      <div class="list-item__image_container">
        <img src='${toUrl(this.state.snapshots[this.currentIndex])}' loading='lazy'/>
      </div>
      <div class="list-item__info">
        <div class="list-item__dirname">${this.state.dirname}</div>
        <div class="list-item__name">${this.state.name}</div>
        <div class="list-item__links">
          <span class="kind-badge badge--video">동영상</span>
          <a target="_blank" href="potplayer://${toPotPath(this.state.target)}">pot</a> |
          <a target="_blank" href="${toUrl(this.state.target)}">browser</a>
        </div>
      </div>
    </div>`;
    const img = target.querySelector("img");
    img.addEventListener("click", () => {
      this.currentIndex++;
      img.src = toUrl(
        this.state.snapshots[this.currentIndex % this.state.snapshots.length],
      );
    });
  };
  render();
}

function ImageItem({ target, initialState }) {
  const render = () => {
    const thumbSrc = initialState.thumbnail || initialState.target;
    target.innerHTML = `
    <div class="list-item__container">
      <div class="list-item__image_container">
        <img src='${toUrl(thumbSrc)}' loading='lazy'/>
      </div>
      <div class="list-item__info">
        <div class="list-item__dirname">${initialState.dirname}</div>
        <div class="list-item__name">${initialState.name}</div>
        <div class="list-item__links">
          <span class="kind-badge badge--image">이미지</span>
        </div>
      </div>
    </div>`;
    const img = target.querySelector("img");
    img.style.cursor = "zoom-in";
    img.addEventListener("click", () => openImageViewer(initialState.target));
  };
  render();
}

// Image viewer
function openImageViewer(src) {
  const viewer = document.getElementById("imageViewer");
  document.getElementById("imageViewerImg").src = toUrl(src);
  viewer.classList.remove("hidden");
  setViewerMode("fit");
}

function closeImageViewer() {
  document.getElementById("imageViewer").classList.add("hidden");
  document.getElementById("imageViewerImg").src = "";
}

function setViewerMode(mode) {
  viewerMode = mode;
  const scroll = document.getElementById("imageViewerScroll");
  scroll.className =
    mode === "fit"
      ? "image-viewer__scroll fit-mode"
      : "image-viewer__scroll original-mode";
  document
    .getElementById("btnFitScreen")
    .classList.toggle("active", mode === "fit");
  document
    .getElementById("btnOriginalSize")
    .classList.toggle("active", mode === "original");
  if (mode === "original") {
    requestAnimationFrame(() => {
      scroll.scrollLeft = (scroll.scrollWidth - scroll.clientWidth) / 2;
      scroll.scrollTop = (scroll.scrollHeight - scroll.clientHeight) / 2;
    });
  }
}

// 원본 크기 모드 드래그 패닝
(function () {
  let dragging = false;
  let startX, startY, scrollLeft, scrollTop;
  const scroll = document.getElementById("imageViewerScroll");

  scroll.addEventListener("mousedown", (e) => {
    if (viewerMode !== "original") return;
    dragging = true;
    hasDragged = false;
    startX = e.clientX;
    startY = e.clientY;
    scrollLeft = scroll.scrollLeft;
    scrollTop = scroll.scrollTop;
    scroll.classList.add("is-dragging");
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasDragged = true;
    scroll.scrollLeft = scrollLeft - dx;
    scroll.scrollTop = scrollTop - dy;
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    scroll.classList.remove("is-dragging");
  });
})();

// Initialize: restore from hash or set root state
(function () {
  if (STANDALONE) {
    updateNav();
    renderApp();
    return;
  }
  const hash = location.hash.slice(1);
  if (hash) {
    const result = findNodeByPath(hash);
    if (result) {
      navStack = result.stack;
      currentNode = result.node;
    }
  }
  history.replaceState(
    { path: getNodePath(currentNode, navStack) },
    "",
    location.hash || "#" + getNodePath(videos, []),
  );
  updateNav();
  renderApp();
})();

window.addEventListener("popstate", (e) => {
  if (STANDALONE) return;
  const path = e.state && e.state.path ? e.state.path : "";
  const result = findNodeByPath(path) || { node: videos, stack: [] };
  navStack = result.stack;
  currentNode = result.node;
  updateNav();
  renderApp();
  window.scrollTo(0, 0);
});

document.getElementById("btnBack").addEventListener("click", () => {
  if (STANDALONE) {
    location.href = "../index.html";
    return;
  }
  if (navStack.length > 0) {
    navigateTo(navStack[navStack.length - 1], navStack.slice(0, -1));
  }
});

document.getElementById("btnToggleView").addEventListener("click", () => {
  viewMode = viewMode === "list" ? "grid" : "list";
  document.getElementById("btnToggleView").textContent =
    viewMode === "list" ? "Grid" : "List";
  renderApp();
});

document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    filterKind = btn.dataset.kind;
    document
      .querySelectorAll(".filter-btn")
      .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderApp();
  });
});

document
  .getElementById("btnFitScreen")
  .addEventListener("click", () => setViewerMode("fit"));
document
  .getElementById("btnOriginalSize")
  .addEventListener("click", () => setViewerMode("original"));
document
  .getElementById("btnCloseViewer")
  .addEventListener("click", closeImageViewer);

document.getElementById("imageViewerScroll").addEventListener("click", (e) => {
  if (hasDragged) {
    hasDragged = false;
    return;
  }
  if (e.target === e.currentTarget) closeImageViewer();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeImageViewer();
});
