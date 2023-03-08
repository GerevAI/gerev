import * as React from "react";

import axios from 'axios';

import { FaConfluence, FaSlack, FaGoogleDrive } from "react-icons/fa";

import EnterImage from './assets/images/enter.svg';
import BlueFolder from './assets/images/blue-folder.svg';
import Yuval from './assets/images/yuval.png';



import './assets/css/App.css';
import SearchBar from "./components/search-bar";


export interface TextPart{
  content: string
  bold: boolean
}

export enum ResultType {
  Docment,
  Comment,
  Person
}

export enum Platform {
  Confluence = "confluence",
  Slack = "slack",
  Drive = "drive"
}

export interface SearchResult {
  title: string 
  author: string
  time: string
  content: TextPart[]
  score: number
  location: string
  platform: string 
  type: ResultType
  url: string
}

export interface AppState {
  query: string
  results: SearchResult[]
  searchDuration: number
  isLoading: boolean
}

const api = axios.create({
  baseURL: `http://${window.location.hostname}:8000`,
})

export default class App extends React.Component <{}, AppState>{

  constructor() {
    super({});
    this.state = {
      isLoading: false,
      query: "Ask any workplace question",
      results: [{content: [{content: "Should end with a", bold: false},
                {content: " Design Review", bold: true},
                {content: " Think of the Plan as a recommendation.", bold: false},], 
                score: 0.5, author: "Yuval Steuer", title: "Infrastructure Rework",
                 url: "https://www.gerev.ai", time: "2021-05-01", platform: "confluence", type: ResultType.Docment,
                location: "Dev Group"},

                {content: [{content: "This", bold: false},
                {content: " Design Review", bold: true},
                {content: " Makes no sense.", bold: false},
                {content: " We should fire this guy ASAP", bold: false},], 
                score: 0.5, author: "Yuval Steuer", title: "Infrastructure Rework",
                  url: "https://www.gerev.ai", time: "2021-05-02", platform: "confluence", type: ResultType.Docment,
                location: "Dev Group"},
      ],
      searchDuration: 0
    }
  }


  render() {
    return (
      <div className="bg-[#181212] w-[99vw] h-screen">
        {/* <div className='absolute'>
          <button onClick={this.startIndex} className='bg-[#886fda] ml-3 text-white p-2 rounded border-2 border-white-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out m-2'>
                Index
          </button>
        </div> */}

        {/* front search page*/}
        {
          this.state.results.length === 0 &&    
            <div className='fixed flex flex-col items-center top-40 mx-auto w-full'>
              <h1 className='text-7xl text-center text-white m-10'>🧦 gerev.ai</h1>
                <SearchBar query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                          onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} />

                <button onClick={this.search} className="h-9 w-28 mt-8 p-3 flex items-center justify-center hover:shadow-sm
                  transition duration-150 ease-in-out hover:shadow-[#6c6c6c] bg-[#2A2A2A] rounded border-[.5px] border-[#6e6e6e88]">
                  <span className="font-bold text-[15px] text-[#B3B3B3]">Search</span>
                  <img className="ml-2" src={EnterImage}></img>
                </button>
            </div>  
        } 

        {/* results page */}
        {
          this.state.results.length > 0 && 
          <div className="fixed flex flex-row top-20 left-5 w-full">
            <span className='text-3xl text-center text-white m-10 mt-0'>🧦 gerev.ai</span>
            <div className="flex flex-col items-start w-10/12">
              <SearchBar query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                        onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} />
              <span className="text-[#D2D2D2] font-poppins font-medium text-base leading-[22px] mt-3">
                {this.state.results.length} Results ({this.state.searchDuration} seconds)
              </span>
              <div className='w-6/12 mt-4 divide-y divide-[#3B3B3B] divide-y-[0.7px]'>
                {this.state.results.map((result, index) => {
                    return (
                      <div className="mb-4 pt-2">
                        <a className="relative text-sm float-right text-white right-2 top-2">{result.score.toFixed(2)}%</a>
                        <div className="flex flex-row items-start">
                          <span>
                            {this.getIconByPlatform(result.platform as Platform)}
                          </span>
                          <p key={index} className='p-2 pt-0 ml-1 text-[#A3A3A3] text-sm font-poppins'>
                            <span className="text-[24px] text-[#EDBB46] text-xl font-poppins font-medium ">{result.title}</span>
                            <span className="flex flex-row text-[15px] font-medium mb-4 mt-1">
                              <img className="inline-block mr-2" src={BlueFolder}></img>
                              <span className="ml-0 text-[#D5D5D5]">{result.location} ·&thinsp;</span>
                              <span className="flex flex-row">
                                <img className="inline-block ml-2 mr-2 h-4" src={Yuval}></img>
                                <span>{result.author} ·</span> 
                              </span>
                              <span>
                                &thinsp;Updated {this.getFormattedTime(result.time)}&thinsp; |&thinsp;
                              </span>
                              <span className="flex flex-row items-center">
                                <FaConfluence className="inline ml-1 mr-2  fill-[#A3A3A3]"></FaConfluence>
                                <span className="text-[#A3A3A3]">Confluence</span>
                              </span>
                            </span>
                            {result.content.map((text_part, index) => {
                              return (
                                <span key={index} className={(text_part.bold ? 'font-bold text-white' : '') + 
                                    " text-md font-poppins font-medium"}>
                                  {text_part.content}
                                </span>
                              )
                            })}
                          </p>
                        </div>
                      </div>
                      )
                    }
                  )}
              </div>
            </div>
          </div>
        }


      </div>
      
    );  
  }

  startIndex = () => {
    try {
        const response = api.post(`/index-confluence`).then(response => {});
    } catch (error) {
      console.error(error);
    }
  }

  handleQueryChange = (query: string) => {
    this.setState({query: query});
  }

  getFormattedTime = (time: string) => {
    let date = new Date(time);
    return date.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'});
  }

  getIconByPlatform = (platform: Platform) => {
    let classes = "inline mt-2 mr-2 text-4xl";
    switch (platform) {
      case Platform.Confluence:
        return <FaConfluence className={classes + " fill-blue-500"}></FaConfluence>
      case Platform.Slack:
        return <FaSlack className={classes}></FaSlack>
      case Platform.Drive:
        return <FaGoogleDrive className={classes}></FaGoogleDrive>
    }
  }
      
  clear = () => {
    this.setState({query: "", results: []});
  }

  search = () => {
    if (this.state.query == "") {
      return;
    }

    this.setState({isLoading: true});
    let start = new Date().getTime();

    try {
        const response = api.get<SearchResult[]>("/search", {
          params: {
            query: this.state.query
          }
        }).then(
          response => {
            if (response.data.length == 0) {
              response.data = [{content: [{content: "No results found", bold: false}], score: 0, author: "", 
              title: "", url: "", platform: "", type: ResultType.Docment, time: "", location: ""}];
            }

            let end = new Date().getTime();
            let duartionSeconds =  (end - start) / 1000;
            this.setState({results: response.data, isLoading: false, searchDuration: duartionSeconds});
          }
        );
    } catch (error) {
      console.error(error);
    }
  };
  
}

