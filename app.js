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
    ul.setAttribute("class", "list-view");

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
      <div class="list-item__label_container">
        <span>
          <a target="_blank" href="potplayer://${this.state.target.replace(
            /\\/gi,
            "/"
          )}">pot</a> | 
          <a target="_blank" href="${this.state.target}">browser</a>
        </span>
      </div>
      <div>
      ${this.state.name}
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

const btn = document.getElementById("btnOpen");
const appElement = document.getElementById("app");
const app = new App(appElement);

app.setState({ videos: videos });

btn.addEventListener("click", async () => {
  const [fileHandle] = await window.showOpenFilePicker();
  const file = await fileHandle.getFile();
  const contents = await file.text();
  const dataJson = JSON.parse(contents);
  app.setState({ videos: dataJson });
});
