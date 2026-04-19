let viewMode = 'grid';
let navStack = [];
let currentNode = videos; // videos is now the tree root node

function renderApp() {
  const appEl = document.getElementById('app');
  appEl.innerHTML = '';

  const ul = document.createElement('ul');
  ul.className = viewMode === 'grid' ? 'list-view grid-view' : 'list-view';

  const dirs = currentNode.children.filter(c => c.type === 'dir');
  const files = currentNode.children.filter(c => c.type === 'file');

  dirs.forEach(dir => {
    const li = document.createElement('li');
    li.className = 'list-item list-item--dir';
    const count = countFiles(dir);
    li.innerHTML = `
      <div class="list-item__container">
        <span class="list-item__dir-icon">&#128193;</span>
        <span class="list-item__name">${dir.name}</span>
        <span class="list-item__dir-count">${count}개 파일</span>
      </div>`;
    li.addEventListener('click', () => {
      navStack.push(currentNode);
      currentNode = dir;
      updateNav();
      renderApp();
      window.scrollTo(0, 0);
    });
    ul.appendChild(li);
  });

  files.forEach(file => {
    const li = document.createElement('li');
    li.className = 'list-item';
    new ListItem({ target: li, initialState: file });
    ul.appendChild(li);
  });

  appEl.appendChild(ul);
}

function countFiles(node) {
  let count = 0;
  for (const child of node.children) {
    if (child.type === 'file') count++;
    else count += countFiles(child);
  }
  return count;
}

function updateNav() {
  const btnBack = document.getElementById('btnBack');
  const breadcrumb = document.getElementById('breadcrumb');
  btnBack.disabled = navStack.length === 0;
  const parts = navStack.map(n => n.name).concat(currentNode.name);
  breadcrumb.textContent = parts.join(' / ');
}

function ListItem({ target, initialState }) {
  this.state = { ...initialState };
  this.currentIndex = 0;
  const render = () => {
    target.innerHTML = `
    <div class="list-item__container">
      <div class="list-item__image_container">
        <img src='${this.state.snapshots[this.currentIndex]}'/>
      </div>
      <div class="list-item__info">
        <div class="list-item__dirname">${this.state.dirname}</div>
        <div class="list-item__name">${this.state.name}</div>
        <div class="list-item__links">
          <a target="_blank" href="potplayer://${this.state.target.replace(/\\/gi, "/")}">pot</a> |
          <a target="_blank" href="${this.state.target}">browser</a>
        </div>
      </div>
    </div>`;
    const img = target.querySelector('img');
    img.addEventListener('click', () => {
      this.currentIndex++;
      img.src = this.state.snapshots[this.currentIndex % this.state.snapshots.length];
    });
  };
  render();
}

// Initialize
updateNav();
renderApp();

document.getElementById('btnBack').addEventListener('click', () => {
  if (navStack.length > 0) {
    currentNode = navStack.pop();
    updateNav();
    renderApp();
    window.scrollTo(0, 0);
  }
});

document.getElementById('btnToggleView').addEventListener('click', () => {
  viewMode = viewMode === 'list' ? 'grid' : 'list';
  document.getElementById('btnToggleView').textContent = viewMode === 'list' ? 'Grid' : 'List';
  renderApp();
});
