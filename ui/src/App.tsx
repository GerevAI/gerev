import * as React from "react";
import { v4 as uuidv4 } from 'uuid';
import posthog from 'posthog-js';
import { Tooltip } from 'react-tooltip'


import EnterImage from './assets/images/enter.svg';
import WarningImage from './assets/images/warning.svg';
import DiscordImage from './assets/images/discord.png';

import { GiSocks } from "react-icons/gi";

import './assets/css/App.css';
import SearchBar from "./components/search-bar";
import { SearchResult, SearchResultDetails } from "./components/search-result";
import { addToSearchHistory } from "./autocomplete";
import DataSourcePanel from "./components/data-source-panel";
import Modal from 'react-modal';
import { api } from "./api";
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { ClipLoader } from "react-spinners";
import { FiSettings } from "react-icons/fi";
import { AiFillWarning } from "react-icons/ai";
import { ConnectedDataSource, DataSourceType } from "./data-source";
import { IoMdArrowDropdown, IoMdClose } from "react-icons/io";
import ProgressBar from "@ramonak/react-progress-bar";

export interface AppState {
  query: string
  results: SearchResultDetails[]
  searchDuration: number
  dataSourceTypes: DataSourceType[]
  dataSourceTypesDict: { [key: string]: DataSourceType }
  didListedDataSources: boolean
  didListedConnectedDataSources: boolean
  connectedDataSources: ConnectedDataSource[]
  isLoading: boolean
  isNoResults: boolean
  isModalOpen: boolean
  isServerDown: boolean
  isStartedFetching: boolean
  isPreparingIndexing: boolean
  isIndexing: boolean
  didPassDiscord: boolean
  discordCodeInput: string
  docsLeftToIndex: number
  docsInIndexing: number
  docsIndexed: number
  timeSinceLastIndexing: number
  serverDownCount: number
  showResultsPage: boolean
  languageOpen: boolean
  showNotReady: boolean
  isFirstTimeIndexing: boolean
  sourceInIndexing: string
}

export interface ServerStatus {
  docs_in_indexing: number
  docs_left_to_index: number
  docs_indexed: number
}

Modal.setAppElement('#root');

const modalCustomStyles = {
  content: {
    top: '50%',
    left: '50%',
    right: 'auto',
    bottom: 'auto',
    marginRight: '-50%',
    transform: 'translate(-50%, -50%)',
    background: '#221f2e',
    width: '52vw',
    border: 'solid #694f94 0.5px',
    borderRadius: '12px',
    height: 'fit-content',
    maxHeight: '86vh',
    padding: '0px'
  },
  overlay: {
    background: '#0000004a'
  },
  special: {
    stroke: 'white'
  }
};

const languages = ["🇫🇷 FR", "🇩🇪 DE", "🇪🇸 ES", "🇮🇹 IT", "🇨🇳 CN", "🌏 GLOBAL"];

export default class App extends React.Component<{}, AppState>{

  constructor() {
    super({});
    this.state = {
      query: "",
      results: [],
      dataSourceTypes: [],
      didListedDataSources: false,
      dataSourceTypesDict: {},
      connectedDataSources: [],
      didListedConnectedDataSources: false,
      isLoading: false,
      isNoResults: false,
      isModalOpen: false,
      isServerDown: false,
      isStartedFetching: false,
      isPreparingIndexing: false,
      discordCodeInput: "",
      didPassDiscord: false,
      docsLeftToIndex: 0,
      docsInIndexing: 0,
      docsIndexed: 0,
      isIndexing: false,
      serverDownCount: 0,
      timeSinceLastIndexing: 0,
      searchDuration: 0,
      showResultsPage: false,
      languageOpen: false,
      showNotReady: false,
      isFirstTimeIndexing: false,
      sourceInIndexing: ""
    }

    this.openModal = this.openModal.bind(this);
    this.closeModal = this.closeModal.bind(this);
  }


  componentDidMount() {
    if (localStorage.getItem('uuid') === null) {
      let uuid = uuidv4();
      localStorage.setItem('uuid', uuid);
    }
    posthog.identify(localStorage.getItem('uuid')!);

    if (localStorage.getItem('discord_key') != null) {
      this.setState({ didPassDiscord: true });
    }

    if (!this.state.isStartedFetching) {
      this.fetchStatsusForever();
      this.setState({ isStartedFetching: true });
      this.listConnectedDataSources();
      this.listDataSourceTypes();
    }

    let firstTimeIndexing = localStorage.getItem('first_time_indexing');
    if (firstTimeIndexing != null) {
      this.setState({ isFirstTimeIndexing: true, sourceInIndexing: firstTimeIndexing, showNotReady: true });
    } else {
      this.handleSearch();
    }

  }

  handleSearch() {
    const path = window.location.pathname;
    const query = new URLSearchParams(window.location.search).get('query');
    if (path === '/search' && query !== null && query !== "") {
      this.setState({ query: query, showResultsPage: true });
      this.search(query);
    }
  }

  async listDataSourceTypes() {
    try {
      const response = await api.get<DataSourceType[]>('/data-sources/types');
      let dataSourceTypesDict: { [key: string]: DataSourceType } = {};
      response.data.forEach((dataSourceType) => {
        dataSourceTypesDict[dataSourceType.name] = dataSourceType;
      });
      this.setState({ dataSourceTypes: response.data, dataSourceTypesDict: dataSourceTypesDict, didListedDataSources: true });
    } catch (error) {
    }
  }

  async listConnectedDataSources() {
    try {
      const response = await api.get<ConnectedDataSource[]>('/data-sources/connected');
      this.setState({ connectedDataSources: response.data, didListedConnectedDataSources: true });
    } catch (error) {
    }
  }

  async fetchStatsusForever() {
    let timeBetweenFailToast = 5;
    let failSleepSeconds = 1;
    api.get<ServerStatus>('/status', { timeout: 3000 }).then((res) => {
      if (this.state.isServerDown) {
        toast.dismiss();
        if (!document.hidden) {
          toast.success("Server online.", { autoClose: 2000 });
        }
        this.listConnectedDataSources();
        this.listDataSourceTypes();
      }

      let isPreparingIndexing = this.state.isPreparingIndexing;
      let isIndexing = this.state.isIndexing;
      let lastIndexingTime = this.state.timeSinceLastIndexing;
      let isFirstTimeIndexing = this.state.isFirstTimeIndexing;
      if (res.data.docs_in_indexing > 0 || res.data.docs_left_to_index > 0 || (res.data.docs_indexed > this.state.docsIndexed && this.state.docsIndexed > 0)) {
        isIndexing = true;
        lastIndexingTime = Date.now();
        isPreparingIndexing = false;
      } else if (isIndexing && Date.now() - lastIndexingTime > (1000 * 10 * 1)) {
        isIndexing = false;
        isFirstTimeIndexing = false;
        this.setState({ showNotReady: false });
        localStorage.removeItem('first_time_indexing');
        toast.success("Indexing finished.", { autoClose: 2000 });
      }

      this.setState({
        isServerDown: false, isFirstTimeIndexing: isFirstTimeIndexing, 
        docsLeftToIndex: res.data.docs_left_to_index,
        docsInIndexing: res.data.docs_in_indexing, isPreparingIndexing: isPreparingIndexing,
        docsIndexed: res.data.docs_indexed, isIndexing: isIndexing, timeSinceLastIndexing: lastIndexingTime
      });

      let timeToSleep = 1000;
      setTimeout(() => this.fetchStatsusForever(), timeToSleep);
    }).catch((err) => {
      this.setState({ serverDownCount: this.state.serverDownCount + 1 });

      if (this.state.serverDownCount > 5 && !document.hidden) {  // if it's 6 seconds since last server down, show a toast
        toast.dismiss();
        toast.error(`Server is not responding (retrying...)`, { autoClose: (timeBetweenFailToast - 1) * 1000 });
        this.setState({ isServerDown: true, serverDownCount: 0 });
      }
      setTimeout(() => this.fetchStatsusForever(), failSleepSeconds * 1000);
    })
  }

  inIndexing() {
    return this.state.isPreparingIndexing || this.state.isIndexing;
  }

  getIndexingStatusText() {
    if (this.state.isPreparingIndexing) {
      return "Indexing process in progress...";
    }

    if (this.state.docsInIndexing > 0) {
      let text = "Indexing " + this.state.docsInIndexing + " documents...";
      if (this.state.docsLeftToIndex > 0) {
        text += " (" + this.state.docsLeftToIndex + " in queue";
        if (this.state.docsIndexed > 0) {
          text += ", " + this.state.docsIndexed + " indexed)";
        } else {
          text += ")";
        }

      } else {
        if (this.state.docsIndexed > 0) {
          text += " (" + this.state.docsIndexed + " indexed)";
        }
      }

      return text;
    }

    if (this.state.docsLeftToIndex > 0) {
      let text = `Fetching docs... (${this.state.docsLeftToIndex} docs in queue`;
      if (this.state.docsIndexed > 0) {
        text += ", " + this.state.docsIndexed + "  indexed)";
      } else {
        text += ")";
      }
      return text;
    }

    return `Indexing... (${this.state.docsIndexed} indexed)`;

  }

  openModal() {
    if (this.state.didPassDiscord) {
      this.setState({ isModalOpen: true });
    } else {
    }
  }

  afterOpenModal() {
    // references are now sync'd and can be accessed.
  }

  closeModal() {
    this.setState({ isModalOpen: false });
  }

  getTitleGradient() {
    if (this.state.isServerDown) {
      return "from-[#333333_24.72%] via-[#333333_50.45%] to-[#333333_74.45%]"
    }

    return "from-[#FFFFFF_24.72%] via-[#B8ADFF_50.45%] to-[#B8ADFF_74.45%]"
  }

  getSocksColor() {
    if (this.state.isServerDown) {
      return " text-[#333333]"
    }

    return " text-[#A78BF6]"
  }

  hideDiscord = () => {
    this.setState({ didPassDiscord: true });
  }

  saveDiscordPassed = (joined: boolean) => {
    localStorage.setItem('discord_key', 'true');
    this.setState({ didPassDiscord: true });
    if (joined) {
      posthog.capture('passed_discord', { name: "joined" });
      toast.success("Welcome to the community!", { autoClose: 2000 });
    } else {
      posthog.capture('passed_discord', { name: "skipped" });
      toast.success("Welcome! use top-left discord icon to join the community.", { autoClose: 8000 });
    }
  }

  dataSourcesAdded = (newlyConnected: ConnectedDataSource) => {
    posthog.capture('added', { name: newlyConnected.name });
    let isFirstTime = false;
    let sourceInIndexing = "";
    if (this.state.connectedDataSources.length === 0) {
      localStorage.setItem('first_time_indexing', newlyConnected.name);
      isFirstTime = true;
      sourceInIndexing = newlyConnected.name;
    }

    this.setState({
      isFirstTimeIndexing: isFirstTime, sourceInIndexing: sourceInIndexing,
      isPreparingIndexing: true, connectedDataSources: [...this.state.connectedDataSources, newlyConnected]
    });
  }

  dataSourceRemoved = (removed: ConnectedDataSource) => {
    posthog.capture('removed', { name: removed.name });
    this.setState({ connectedDataSources: this.state.connectedDataSources.filter((ds) => ds.id !== removed.id) });
  }

  render() {
    return (
      <div>
        <Tooltip id="my-tooltip" style={{ fontSize: "18px" }} />
        <ToastContainer className='z-50' theme="colored" />
        <a href="https://discord.gg/NKhTX7JZAF" rel="noreferrer" target='_blank'>
          <img data-tooltip-id="my-tooltip" src={DiscordImage}
            data-tooltip-content="Click for 24/7🕒 live support 👨‍🔧💬"
            data-tooltip-place="bottom" alt="discord"
            className="absolute left-0 z-30 h-7 hover:fill-[#a7a1fe] fill-[#8983e0] float-left ml-6 mt-6 text-[42px] hover:cursor-pointer transition-all duration-300 hover:drop-shadow-2xl">
          </img>
        </a>
        <span className={"absolute right-0 z-30 float-right mr-6 mt-6 flex flex-row " + (this.state.languageOpen ? "items-start" : "items-center")}>
          <span className="flex flex-col mr-4 bg-[#4f476cb9] border-2 rounded-xl border-[#443f57]">
            <span onClick={() => { this.setState({ languageOpen: !this.state.languageOpen }) }} className="flex justify-between flex-row items-center px-2 rounded-xl
              hover:cursor-pointer hover:drop-shadow-2xl transition-all duration-100 hover:bg-[#7b70a4b9] hover:border-[#787099]">
              {/* <a className="text-xl text-white mr-2">EN</a> */}
              {/* <img src={UsaImage} className="h-8 text-[42px] grayscale-[0.5]"/> */}
              <span className="text-[20px] text-white">🇺🇸 {this.state.languageOpen ? "EN" : ""}</span>
              <IoMdArrowDropdown className={"ml-1 fill-white text-[22px] transition-all duration-300 " +
                (this.state.languageOpen ? "rotate-180" : "")}></IoMdArrowDropdown>
            </span>
            {this.state.languageOpen &&
              <div className="flex flex-col text-white">
                {
                  languages.map((lang) => {
                    return (
                      <a href="https://gerev.typeform.com/languages" target="_blank"
                        rel="noreferrer" className="text-[20px] px-2 py-1 rounded-xl hover:cursor-pointer hover:drop-shadow-2xl transition-all duration-100
                  hover:bg-[#7b70a4b9] hover:border-[#787099] text-start">{lang}</a>
                    )
                  })
                }
              </div>
            }
          </span>

          <FiSettings onClick={this.openModal} stroke={"#8983e0"}
            className="mr-2 text-[42px] hover:cursor-pointer hover:rotate-90 transition-all duration-300 hover:drop-shadow-2xl">
          </FiSettings>
        </span>
        {
          this.inIndexing() &&
          <div className="absolute mx-auto left-0 right-0 w-fit z-20 top-6">
            <div className="text-xs bg-[#191919] border-[#4F4F4F] border-[.8px] rounded-full inline-block px-3 py-1">
              <div className="text-[#E4E4E4] font-medium font-inter text-sm flex flex-row justify-center items-center">
                <ClipLoader color="#ffffff" loading={true} size={14} aria-label="Loading Spinner" />
                <span className="ml-2">{this.getIndexingStatusText()}</span>
              </div>
            </div>
          </div>
        }
        {/* Go add some data sources ->*/
          this.state.didListedConnectedDataSources && this.state.connectedDataSources.length === 0 && this.state.didPassDiscord &&
          <div className="absolute mx-auto left-0 right-0 w-fit z-20 top-6">
            <div className="text-xs bg-[#100101] border-[#a61616] border-[.8px] rounded-full inline-block px-3 py-1">
              <div className="text-[#E4E4E4] font-medium font-inter text-sm flex flex-row justify-center items-center">
                <AiFillWarning color="red" size={20} />
                <span className="ml-2">No sources added. </span>
                <button className="font-medium ml-1 text-[red] animate-pulse hover:cursor-pointer inline-flex items-center transition duration-150 ease-in-out group"
                  onClick={this.openModal}>
                  Go add some{' '}
                  <span className="tracking-normal group-hover:translate-x-0.5 transition-transform duration-150 ease-in-out ml-1">-&gt;</span>
                </button>
              </div>
            </div>
          </div>
        }
        {/* Discord page */}
        {
          !this.state.didPassDiscord &&
          <div className='absolute z-30 flex flex-col items-center top-40 mx-auto w-full'>
            <div className="flex flex-col items-start w-[660px] h-[305px] bg-[#36393F] rounded-xl">
              <div className="flex flex-col justify-center items-start  p-3">
                <div className="ml-[614px] text-2xl text-white gap-4">
                  <IoMdClose onClick={this.hideDiscord} className='hover:text-[#9875d4] hover:cursor-pointer' />
                </div>
                <span className="flex flex-row text-white text-3xl font-bold m-5 mt-5 mb-6 font-sans items-center">
                  <span>Are you on Discord?</span>
                  <img src={DiscordImage} alt="discord" className="relative inline h-10 ml-4 opacity-80 animate-pulse"></img>
                </span>
                <div className="flex flex-row w-[97%] bg-[#faa61a1a] p-3 ml-1 border-[2px] border-[#FAA61A] rounded-[5px]">
                  <img className="ml-2 h-10" src={WarningImage} alt="warning"></img>
                  <button className="ml-4 text-white text-xl font-source-sans-pro font-semibold inline">
                    <span className="block text-left">Join Gerev's 1000+ discord community members, get early access to exclusive features.
                      <a href="https://discord.gg/aMRRcmhAdW" target="_blank" rel="noreferrer"
                        className="inline-flex transition duration-150 ease-in-out group ml-1 hover:cursor-pointer">Join Discord
                        <span className="font-inter tracking-normal font-semibold group-hover:translate-x-0.5 transition-transform duration-150 ease-in-out ml-1">-&gt;</span>
                      </a>
                    </span>
                  </button>
                </div>
              </div>
              <div className="flex flex-row justify-between p-4 w-[100%]  mt-7 rounded-b-xl h-[100px] bg-[#2F3136]">
                <button onClick={() => { this.saveDiscordPassed(false) }} className="font-inter bg-[#4f545d] hover:bg-[#3a3e45] rounded h-12 p-2 text-white w-40">Hide forever</button>

                <a onClick={() => { this.saveDiscordPassed(true) }} href="https://discord.gg/aMRRcmhAdW" target="_blank" rel="noreferrer" className="flex hover:bg-[#404ab3] justify-center items-center font-inter bg-[#5865F2] rounded h-12 p-2 text-white w-40 
                    inline-flex transition duration-150 ease-in-out group ml-1 hover:cursor-pointer">Join Discord
                  <span className="font-inter tracking-normal font-semibold group-hover:translate-x-0.5 transition-transform duration-150 ease-in-out ml-1">-&gt;</span>
                </a>
              </div>
            </div>

          </div>
        }
        {/* Not ready yet page */}
        {
          this.state.showNotReady &&
          <div className='absolute z-30 flex flex-col items-center top-[200px] mx-auto w-full'>
            <div className="flex flex-col items-center w-[660px] h-[280px] bg-[#211a2e] border-[1px] border-[#3f3066] rounded-xl">
              <div className="flex flex-col justify-center items-center py-2">
                <div className="ml-[614px] text-2xl text-[#4d3e88] gap-4">
                  <IoMdClose onClick={() => this.setState({ showNotReady: false })} className='hover:text-[#6d59bd] hover:cursor-pointer' />
                </div>
                <span className="flex flex-row text-white text-3xl font-bold m-5 mt-5 mb-1 font-sans items-center">
                  <span className="text-[#7e6ab8] text-3xl">Not ready yet!</span>
                </span>
                <span className="text-[#695c8d] text-lg">Gerev won't be usefull until we finish indexing your workplace.</span>
                <span className="text-[#aba2f2] text-xl mt-10 font-semibold">{this.capitilize(this.state.sourceInIndexing)}
                  <span className="font-medium"> ({this.state.docsIndexed}/{this.state.docsIndexed + this.state.docsInIndexing + this.state.docsLeftToIndex + 1})</span>...
                </span>
                <ProgressBar completed={parseInt((this.state.docsIndexed / (this.state.docsIndexed + this.state.docsInIndexing + this.state.docsLeftToIndex + 1) * 100).toFixed(2))}
                  bgColor={"#7d3fff"} baseBgColor={"#483982"} className="w-[450px] mt-5" />;
              </div>
            </div>
          </div>
        }
        <div className={"w-[98vw] z-10 filter" + (this.state.isModalOpen || (this.state.didListedConnectedDataSources && this.state.connectedDataSources.length === 0) ? ' filter blur-sm' : '')}>
          <Modal
            isOpen={this.state.isModalOpen}
            onRequestClose={this.closeModal}
            contentLabel="Example Modal"
            style={modalCustomStyles}>
            <DataSourcePanel onClose={this.closeModal} connectedDataSources={this.state.connectedDataSources}
              inIndexing={this.inIndexing()}
              onAdded={this.dataSourcesAdded} dataSourceTypesDict={this.state.dataSourceTypesDict} onRemoved={this.dataSourceRemoved} />
          </Modal>

          {/* front search page*/}
          {
            !this.state.showResultsPage &&
            <div className='relative flex flex-col items-center top-40 mx-auto w-full'>
              <h1 className='flex flex-row items-center text-7xl text-center text-white m-10'>
                <GiSocks className={('text-7xl text-center mt-4 mr-7' + this.getSocksColor())}></GiSocks>
                <span className={("text-transparent	block font-source-sans-pro md:leading-normal bg-clip-text bg-gradient-to-l " + this.getTitleGradient())}>
                  gerev.ai
                </span>
              </h1>
              <SearchBar widthPercentage={32} isDisabled={this.state.isServerDown} query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                onSearch={this.goSearchPage} onQueryChange={this.handleQueryChange} onClear={this.clear} showSuggestions={true} />

              <button onClick={this.goSearchPage} className="h-9 w-28 mt-8 p-3 flex items-center justify-center hover:shadow-sm
                  transition duration-150 ease-in-out hover:shadow-[#6c6c6c] bg-[#2A2A2A] rounded border-[.5px] border-[#6e6e6e88]">
                <span className="font-bold text-[15px] text-[#B3B3B3]">Search</span>
                <img alt="enter" className="ml-2" src={EnterImage}></img>
              </button>
            </div>
          }

          {/* results page */}
          {
            this.state.showResultsPage &&
            <div className="relative flex flex-row top-20 left-5 w-full sm:w-11/12">
              <span className='flex flex-row items-start text-3xl text-center text-white m-10 mx-7 mt-0'>
                <GiSocks className='text-4xl text-[#A78BF6] mx-3 my-1'></GiSocks>
                <span className="text-transparent	block font-source-sans-pro md:leading-normal bg-clip-text bg-gradient-to-l from-[#FFFFFF_24.72%] to-[#B8ADFF_74.45%]">gerev.ai</span>
              </span>
              <div className="flex flex-col items-start w-full sm:w-10/12">
                <SearchBar widthPercentage={40} isDisabled={this.state.isServerDown} query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                  onSearch={this.goSearchPage} onQueryChange={this.handleQueryChange} onClear={this.clear} showSuggestions={true} />
                {
                  !this.state.isLoading &&
                  <span className="text-[#D2D2D2] font-poppins font-medium text-base leading-[22px] mt-3">
                    {this.state.results.length} Results ({this.state.searchDuration} seconds)
                  </span>
                }
                {
                  this.state.dataSourceTypes.length > 0 &&
                  <div className='w-[100vw] 2xl:w-10/12 divide-y divide-[#3B3B3B] divide-y-[0.7px]'>
                    {this.state.results.map((result, index) => {
                      return (
                        <SearchResult key={index} resultDetails={result} dataSourceType={this.state.dataSourceTypesDict[result.data_source]} />
                      )
                    }
                    )}
                  </div>
                }
              </div>
            </div>
          }


        </div>
      </div>


    );
  }

  capitilize(str: string) {
    return str.charAt(0).toUpperCase() + str.slice(1);
 }

  handleQueryChange = (query: string) => {
    this.setState({ query: query });
  }

  clear = () => {
    this.setState({ query: "" });
  }

  showNotReady = () => {
    this.setState({ showNotReady: true });
  }

  goSearchPage = () => {
    if (this.state.isFirstTimeIndexing) {
      this.showNotReady();
      posthog.capture('blocked_premature_search');
      return;
    }
    window.location.replace(`/search?query=${this.state.query}`);
  }

  search = (query?: string) => {
    if (this.state.isFirstTimeIndexing) {
      this.showNotReady();
      posthog.capture('blocked_premature_search');
      return;
    }

    if (!query && this.state.query === "") {
      console.log("empty query");
      return;
    }

    let searchQuery = query ? query : this.state.query;

    this.setState({ isLoading: true });
    let start = new Date().getTime();

    posthog.capture('search');

    try {
      api.get<SearchResultDetails[]>("/search", {
        params: {
          query: searchQuery
        },
        headers: {
          uuid: localStorage.getItem('uuid')
        }
      }
      ).then(
        response => {
          let end = new Date().getTime();
          let duartionSeconds = (end - start) / 1000;
          this.setState({
            results: response.data, isLoading: false, searchDuration: duartionSeconds,
            showResultsPage: response.data.length > 0,
          });
          addToSearchHistory(searchQuery);

          if (response.data.length === 0) {
            toast.warn("No results found");
          }
        }
      );
    } catch (error) {
      toast.error("Error searching: " + error.response.data, { autoClose: 10000 });
    }
  };

}

