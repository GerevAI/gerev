import * as React from "react";

import axios from 'axios';

import { FaConfluence, FaSlack, FaGoogleDrive } from "react-icons/fa";

import EnterImage from './assets/images/enter.svg';


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
  content: TextPart[]
  score: number
  author: string
  title: string 
  url: string
  time: string
  platform: string 
  type: ResultType
}

export interface AppState {
  query: string
  results: SearchResult[]
  isLoading: boolean
}

const api = axios.create({
  baseURL: `http://${window.location.hostname}:8000`,
})

export default class App extends React.Component <{}, AppState>{

  constructor() {
    super({});
    this.state = {query: "Ask any workplace question", results: [], isLoading: false};
  }


  render() {
    return (
      <div className="bg-[#181212] w-[99vw] h-screen flex">
        <div className='absolute'>
          <button onClick={this.startIndex} className='bg-[#886fda] ml-3 text-white p-2 rounded border-2 border-white-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out m-2'>
                Index
          </button>
        </div>
        <div className='flex flex-col items-center mx-auto my-40 w-full'>
          <h1 className='text-7xl text-center text-white m-10'>🧦 gerev.ai</h1>
            <SearchBar query={this.state.query} isLoading={this.state.isLoading} showReset={this.state.results.length > 0}
                       onSearch={this.search} onQueryChange={this.handleQueryChange} onClear={this.clear} />

            <button onClick={this.search} className="h-9 w-28 mt-8 p-3 flex items-center justify-center hover:shadow-sm
               transition duration-150 ease-in-out hover:shadow-[#6c6c6c] bg-[#2A2A2A] rounded border-[.5px] border-[#6e6e6e88]">
              <span className="font-bold text-[15px] text-[#B3B3B3]">Search</span>
              <img className="ml-2" src={EnterImage}></img>
            </button>
       
            <div className='w-7/12 mt-4'>
              {this.state.results.map((result, index) => {
                return (
                  <div>
                    <a className="relative text-sm float-right text-white right-2 top-2">{result.score.toFixed(2)}%</a>
                    <p key={index} className='p-2 text-[#9D9D9D] mt-2'>
                      <span className="text-[24px] text-white font-semibold flex items-center">
                        {this.getIconByPlatform(result.platform as Platform)} {result.title}
                      </span>
                      <span className="text-[15px] text-white font-medium block">
                        (by {result.author}, {this.getFormattedTime(result.time)})
                      </span>
                      {result.content.map((text_part, index) => {
                        return (
                          <span key={index} className={(text_part.bold ? 'font-bold text-white' : '') + " text-md font-poppins font-medium"}>
                            {text_part.content}
                          </span>
                        )
                      })}
                    </p>
                  </div>
                  )
              })}
            </div>
        </div>
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
    return date.toLocaleString();
  }

  getIconByPlatform = (platform: Platform) => {
    let classes = "inline mr-2 text-2xl";
    switch (platform) {
      case Platform.Confluence:
        return <FaConfluence className={classes + " fill-blue-700"}></FaConfluence>
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

    try {
        const response = api.get<SearchResult[]>("/search", {
          params: {
            query: this.state.query
          }
        }).then(
          response => {
            if (response.data.length == 0) {
              response.data = [{content: [{content: "No results found", bold: false}], score: 0, author: "", 
              title: "", url: "", platform: "", type: ResultType.Docment, time: ""}];
            }
            this.setState({results: response.data, isLoading: false});
          }
        );
    } catch (error) {
      console.error(error);
    }
  };
  
}

