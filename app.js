let viewMode = 'grid';

function App(app) {
  this.state = {
    videos: [],
  };

  this.setState = (newState) => {
    this.state = newState;
    this.render();
  };

  this.render = () => {
    new ListView({ target: app, initialState: this.state });
  };

  this.render();
}

function ListView({ target, initialState }) {
  this.state = initialState;
  const setState = (newState) => {
    this.state = newState;
    this.render();
  };
  const render = () => {
    target.innerHTML = "";
    const ul = document.createElement("ul");
    ul.setAttribute("class", viewMode === 'grid' ? "list-view grid-view" : "list-view");

    this.state.videos.map((item) => {
      const li = document.createElement("li");
      li.setAttribute("class", "list-item");
      new ListItem({ target: li, initialState: item });
      ul.appendChild(li);
    });

    target.appendChild(ul);
  };
  render();
}

function ListItem({ target, initialState }) {
  //this.state = { target: undefined, snapshots: [] };
  this.state = { ...initialState };
  this.currentIndex = 0;
  const setState = (newState) => {
    this.state = newState;
    this.render();
  };
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
    </div>
    `;

    const img = target.querySelector("img");
    img.addEventListener("click", () => {
      console.log(this.state.target);
      this.currentIndex++;
      img.src =
        this.state.snapshots[this.currentIndex % this.state.snapshots.length];
    });
  };
  render();
}

const appElement = document.getElementById("app");
const app = new App(appElement);

app.setState({ videos: videos });

const btnToggleView = document.getElementById("btnToggleView");
btnToggleView.addEventListener("click", () => {
  viewMode = viewMode === 'list' ? 'grid' : 'list';
  btnToggleView.textContent = viewMode === 'list' ? 'Grid' : 'List';
  app.render();
});
