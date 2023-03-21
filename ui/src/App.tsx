import * as React from "react";
import { v4 as uuidv4 } from 'uuid';
import posthog from 'posthog-js';



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
import {AiFillWarning} from "react-icons/ai";
import { DataSourceType } from "./data-source";

export interface AppState {
  uuid: string
  query: string
  results: SearchResultDetails[]
  searchDuration: number
  dataSourceTypes: DataSourceType[]
  dataSourceTypesDict: { [key: string]: DataSourceType }
  connectedDataSources: string[]
  isLoading: boolean
  isNoResults: boolean
  isModalOpen: boolean
  isServerDown: boolean
  isStartedFetching: boolean
  isPreparingIndexing: boolean
  didPassDiscord: boolean
  discordCodeInput: string
  docsLeftToIndex: number
  docsInIndexing: number
  lastServerDownTimestamp: number
}

export interface ServerStatus {
  docs_in_indexing: number
  docs_left_to_index: number
}

Modal.setAppElement('#root');

const discordCode = "gerev-is-pronounced-with-a-hard-g";

const customStyles = {
  content: {
    top: '50%',
    left: '50%',
    right: 'auto',
    bottom: 'auto',
    marginRight: '-50%',
    transform: 'translate(-50%, -50%)',
    background: '#221f2e',
    width: '50vw',
    border: 'solid #694f94 0.5px',
    borderRadius: '12px',
    padding: '0px'
  },
  overlay: {
    background: '#0000004a'
  },
  special: {
    stroke: 'white'
  }
};

export default class App extends React.Component <{}, AppState>{

  constructor() {
    super({});
    this.state = {
      uuid: "",
      query: "",
      results: [],
      dataSourceTypes: [],
      dataSourceTypesDict: {},
      connectedDataSources: [],
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
      searchDuration: 0,
      lastServerDownTimestamp: 0,
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
      this.setState({didPassDiscord: true});
    }
    
    if (!this.state.isStartedFetching) {
      this.fetchStatsusForever();
      this.setState({isStartedFetching: true});
      this.listConnectedDataSources();
      this.listDataSourceTypes();
    }
  }

  async listDataSourceTypes() {
    try {
      const response = await api.get<DataSourceType[]>('/data-source/list-types');
      let dataSourceTypesDict: { [key: string]: DataSourceType } = {};
      response.data.forEach((dataSourceType) => { 
        dataSourceTypesDict[dataSourceType.name] = dataSourceType;
      });
      this.setState({ dataSourceTypes: response.data, dataSourceTypesDict: dataSourceTypesDict });
    } catch (error) {
    }
  }

  async listConnectedDataSources() {
    try {
       const response = await api.get('/data-source/list-connected');
       this.setState({ connectedDataSources: response.data })
    } catch (error) {
    }
  }

  async fetchStatsusForever() {
    let successSleepSeconds = 5;
    let timeBetweenFailToast = 5;
    let failSleepSeconds = 1;

    api.get<ServerStatus>('/status').then((res) => {
      if (this.state.isServerDown) {
        toast.dismiss();
        if (!document.hidden) {
          toast.success("Server online.", {autoClose: 2000});
        }
        this.listConnectedDataSources();
      }

      let isPreparingIndexing = this.state.isPreparingIndexing;
      if (this.state.isPreparingIndexing && (res.data.docs_in_indexing > 0 || res.data.docs_left_to_index > 0)) {
        isPreparingIndexing = false;
      }

      if(this.state.docsInIndexing > 0 && (res.data.docs_in_indexing === 0 && res.data.docs_left_to_index === 0)) {
        toast.success("Indexing finished.", {autoClose: 2000});
      }

      this.setState({isServerDown: false, docsLeftToIndex: res.data.docs_left_to_index,
                     docsInIndexing: res.data.docs_in_indexing, isPreparingIndexing: isPreparingIndexing});

      let timeToSleep = isPreparingIndexing ? 1000 : successSleepSeconds * 1000;
      setTimeout(() => this.fetchStatsusForever(), timeToSleep);
    }).catch((err) => {
      this.setState({isServerDown: true});

      if (Date.now() - this.state.lastServerDownTimestamp > 6000 && !document.hidden) {  // if it's 6 seconds since last server down, show a toast
        toast.dismiss();
        toast.error(`Server is down, retrying in ${timeBetweenFailToast} seconds...`, {autoClose: (timeBetweenFailToast-1) * 1000});
        this.setState({lastServerDownTimestamp: Date.now()});
      }
      setTimeout(() => this.fetchStatsusForever(), failSleepSeconds * 1000);
    })    
  }

  shouldShowIndexingStatus() {
    return this.state.isPreparingIndexing || this.state.docsInIndexing > 0 || this.state.docsLeftToIndex > 0;
  }

  getIndexingStatusText() {
    if (this.state.isPreparingIndexing) {
      return "Indexing process in progress...";
    }

    if (this.state.docsInIndexing > 0) {
      let text = "Indexing " + this.state.docsInIndexing + " documents... it might take a while.";
      if (this.state.docsLeftToIndex > 0) {
        text += " (" + this.state.docsLeftToIndex * 10  + "~ left in queue)";
      }

      return text;
    }

    if (this.state.docsLeftToIndex > 0) {
      return "Preparing to index...";
    }
  }
  
  openModal() {
    if (this.state.didPassDiscord) {
      this.setState({isModalOpen: true});
    } else {
      toast.error("You must pass the discord verification first.", {autoClose: 3000});
    }
  }

  afterOpenModal() {
    // references are now sync'd and can be accessed.
  }

  closeModal() {
    this.setState({isModalOpen: false});
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

  verifyDiscordCode = () => {
    if (this.state.discordCodeInput.trim() === discordCode) {
      this.saveDiscordPassed();
    } else {
      toast.error("Invalid code. Join Discord!", {autoClose: 2000});
    }
  }

  onDiscordCodeChange = (event) => {
    if (event.target.value === discordCode) {
      this.saveDiscordPassed();
    } else {
      this.setState({discordCodeInput: event.target.value});
    }
  }

  saveDiscordPassed = () => {
    localStorage.setItem('discord_key', 'true');
    this.setState({didPassDiscord: true});
    toast.success("Code accepted. Welcome!", {autoClose: 3000});
  }

  dataSourcesAdded = (dataSourceType: string) => {
    this.setState({isPreparingIndexing: true, connectedDataSources: [...this.state.connectedDataSources, dataSourceType]});
    // if had no data from server, show toast after 30 seconds
    setTimeout(() => {
      if (this.state.isPreparingIndexing) {
        this.setState({isPreparingIndexing: false})
        toast.success("Indexing finished.", {autoClose: 2000});
      }
    }, 30000);
  }

  render() {
    return (
    <div>
      <ToastContainer className='z-50' theme="colored" />
      <FiSettings onClick={this.openModal} stroke={"#8983e0"} 
        className="absolute right-0 z-30 float-right mr-6 mt-6 text-[42px] hover:cursor-pointer hover:rotate-90 transition-all duration-300 hover:drop-shadow-2xl">
      </FiSettings>
        {
          this.shouldShowIndexingStatus() &&
          <div className="absolute mx-auto left-0 right-0 w-fit z-20 top-6">
            <div className="text-xs bg-[#191919] border-[#4F4F4F] border-[.8px] rounded-full inline-block px-3 py-1">
              <div className="text-[#E4E4E4] font-medium font-inter text-sm flex flex-row justify-center items-center">
                <ClipLoader color="#ffffff" loading={true} size={14} aria-label="Loading Spinner"/>
                <span className="ml-2">{this.getIndexingStatusText()}</span>
              </div>
            </div>
          </div>
        }
        {
          this.state.connectedDataSources.length === 0 && this.state.didPassDiscord &&
          <div className="absolute mx-auto left-0 right-0 w-fit z-20 top-6">
            <div className="text-xs bg-[#100101] border-[#a61616] border-[.8px] rounded-full inline-block px-3 py-1">
              <div className="text-[#E4E4E4] font-medium font-inter text-sm flex flex-row justify-center items-center">
                <AiFillWarning color="red" size={20}/>
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
              <div className="flex flex-col items-start w-[660px] h-[440px] bg-[#36393F] rounded-xl">
                <div className="flex flex-col justify-center items-start  p-3">
                  <span className="flex flex-row text-white text-3xl font-bold m-5 mt-5 mb-6 font-sans items-center">
                    <span>Are you on Discord?</span>
                    <img src={DiscordImage} alt="discord" className="relative inline h-10 ml-4 opacity-80 animate-pulse"></img>
                  </span>
                    <div className="flex flex-row w-[97%] bg-[#faa61a1a] p-3 ml-1 border-[2px] border-[#FAA61A] rounded-[5px]">
                      <img className="ml-2 h-10" src={WarningImage} alt="warning"></img>
                      <button className="ml-4 text-white text-xl font-source-sans-pro font-semibold inline">
                        <span className="block text-left">gerev.ai is currently only available to our Discord community members.
                          <a href="https://discord.gg/aMRRcmhAdW" target="_blank" rel="noreferrer" className="inline-flex transition duration-150 ease-in-out group ml-1 hover:cursor-pointer">Join Discord
                            <span className="font-inter tracking-normal font-semibold group-hover:translate-x-0.5 transition-transform duration-150 ease-in-out ml-1">-&gt;</span>
                          </a>
                        </span>
                      </button>
                    </div>
                    <div className="flex flex-col items-start justify-center ml-2 mt-9 w-[100%]">
                      <span className="text-[#B9BBBE] font-source-sans-pro font-black text-[22px]">ENTER DISCORD AUTH CODE</span>
                      <input onPaste={this.onDiscordCodeChange} value={this.state.discordCodeInput} onChange={this.onDiscordCodeChange} className="bg-[#18191C] h-14 font-source-sans-pro font-black text-xl text-[#DCDDDE] rounded w-[94%] px-4 mt-4" placeholder="123456"></input>
                    </div>
                </div>      
                <div className="flex flex-row justify-between p-4 w-[100%]  mt-7 rounded-b-xl h-[100px] bg-[#2F3136]">
                  <a href="https://discord.gg/aMRRcmhAdW" target="_blank" rel="noreferrer" className="flex hover:bg-[#404ab3] justify-center items-center font-inter bg-[#5865F2] rounded h-12 p-2 text-white w-40 inline-flex transition duration-150 ease-in-out group ml-1 hover:cursor-pointer">Join Discord
                    <span className="font-inter tracking-normal font-semibold group-hover:translate-x-0.5 transition-transform duration-150 ease-in-out ml-1">-&gt;</span>
                  </a>
                  <button onClick={this.verifyDiscordCode} className="font-inter bg-[#5865F2] hover:bg-[#404ab3] rounded h-12 p-2 text-white w-40">Verify</button>
                </div>
              </div>

            </div>
        }
      <div className={"w-[98vw] z-10 filter" + (this.state.isModalOpen || this.state.connectedDataSources.length === 0  ? ' filter blur-sm' : '')}>
        <Modal
          isOpen={this.state.isModalOpen}
          onRequestClose={this.closeModal}
          contentLabel="Example Modal"
          style={customStyles}>
          <DataSourcePanel onClose={this.closeModal} connectedDataSources={this.state.connectedDataSources}
            onAdded={this.dataSourcesAdded} dataSourceTypesDict={this.state.dataSourceTypesDict}/>
        </Modal>

        {/* front search page*/}
        {
          this.state.results.length === 0 &&    
            <div className='relative flex flex-col items-center top-40 mx-auto w-full'>
                <h1 className='flex flex-row items-center text-7xl text-center text-white m-10'>                
                  <GiSocks className={('text-7xl text-center mt-4 mr-7' + this.getSocksColor())}></GiSocks>
                  <span className={("text-transparent	block font-source-sans-pro md:leading-normal bg-clip-text bg-gradient-to-l " + this.getTitleGradient())}>
                    gerev.ai
                  </span>
                </h1>
                <SearchBar widthPercentage={32} isDisabled={this.state.isServerDown} query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                          onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} showSuggestions={true} />

                <button onClick={this.search} className="h-9 w-28 mt-8 p-3 flex items-center justify-center hover:shadow-sm
                  transition duration-150 ease-in-out hover:shadow-[#6c6c6c] bg-[#2A2A2A] rounded border-[.5px] border-[#6e6e6e88]">
                  <span className="font-bold text-[15px] text-[#B3B3B3]">Search</span>
                  <img alt="enter" className="ml-2" src={EnterImage}></img>
                </button>
                { this.state.isNoResults && 
                  <span className="text-[#D2D2D2] font-poppins font-medium text-base leading-[22px] mt-3">
                  </span>
                }
            </div>  
        } 

        {/* results page */}
        {
          this.state.results.length > 0 && 
          <div className="relative flex flex-row top-20 left-5 w-full sm:w-11/12">
            <span className='flex flex-row items-start text-3xl text-center text-white m-10 mx-7 mt-0'>
              <GiSocks className='text-4xl text-[#A78BF6] mx-3 my-1'></GiSocks>
              <span className="text-transparent	block font-source-sans-pro md:leading-normal bg-clip-text bg-gradient-to-l from-[#FFFFFF_24.72%] to-[#B8ADFF_74.45%]">gerev.ai</span>
            </span>
            <div className="flex flex-col items-start w-10/12 sm:w-full">
              <SearchBar widthPercentage={40} isDisabled={this.state.isServerDown}  query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                        onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} showSuggestions={true} />
              <span className="text-[#D2D2D2] font-poppins font-medium text-base leading-[22px] mt-3">
                {this.state.results.length} Results ({this.state.searchDuration} seconds)
              </span>
              <div className='w-6/12 sm:w-8/12 mt-4 divide-y divide-[#3B3B3B] divide-y-[0.7px]'>
                {this.state.results.map((result, index) => {
                    return (
                      <SearchResult key={index} resultDetails={result} dataSourceType={this.state.dataSourceTypesDict[result.data_source]} />
                      )
                    }
                  )}
              </div>
            </div>
          </div>
        }


      </div>
      </div>

      
    );  
  }

  handleQueryChange = (query: string) => {
    this.setState({query: query});
  }
  
  clear = () => {
    this.setState({query: "", results: []});
  }

  search = () => {
    if (this.state.query === "") {
      return;
    }

    this.setState({isLoading: true});
    let start = new Date().getTime();

    posthog.capture('search');

    try {
        api.get<SearchResultDetails[]>("/search", {
          params: {
            query: this.state.query
          }}
        ).then(
          response => {
            let end = new Date().getTime();
            let duartionSeconds =  (end - start) / 1000;
            this.setState({results: response.data, isLoading: false, searchDuration: duartionSeconds,
              isNoResults: response.data.length === 0
            });
            addToSearchHistory(this.state.query);
          }
        );
    } catch (error) {
      console.error(error);
    }
  };
  
}

