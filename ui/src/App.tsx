import * as React from "react";

import axios from 'axios';
import ClipLoader from "react-spinners/ClipLoader";
import { BsSearch } from "react-icons/bs";
import { FaConfluence, FaSlack, FaGoogleDrive } from "react-icons/fa";

import './App.css';


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

export default class App extends React.Component <{}, AppState>{

  constructor() {
    super({});
    this.state = {query: "Who is the CEO of Gitlab?", results: [], isLoading: false};
  }


  render() {
    return (
      <div className="bg-[#a5a5a5d1] w-screen h-screen flex">
        <div className='absolute'>
          <button onClick={this.startIndex} className='bg-[#886fda] ml-3 text-white p-2 rounded border-2 border-white-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out m-2'>
                Index
          </button>
        </div>
        <div className='mx-auto my-10'>
          <h1 className='text-7xl text-center m-10'>gerev.ai 🧦</h1>
          <div className='flex flex-col container text-3xl p-4 rounded bg-[#ddddddd1] text-white border-2
                         border-slate-700'>
            <div className='flex'>
              {this.state.results.length > 0 &&
              <a onClick={this.clear} className='text-black mr-2 p-2 cursor-pointer  hover:text-white transition'> 
                X
              </a>
              }
              <input type="text" className='w-full p-2 rounded bg-[#ddddddd1] text-black border-2 border-slate-700'
                     placeholder='Search' value={this.state.query} onChange={this.handleChange} onKeyDown={this.onKeyDown} />
              <button onClick={this.search} className='bg-[#060117] ml-3 text-white p-2 rounded border-2 border-slate-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out flex items-center'>
                <span className='text-3xl mr-2'>Search</span>
                {this.state.isLoading ?
                <ClipLoader
                  color="#ffffff"
                  loading={this.state.isLoading}
                  size={30}
                  aria-label="Loading Spinner"
                /> : <BsSearch></BsSearch>}
              </button>
            </div>

            <div className='w-full mt-4'>
              {this.state.results.map((result, index) => {
                return (
                  <div>
                    <a className="relative text-sm float-right text-black right-2 top-2">{result.score.toFixed(2)}%</a>
                    <p key={index} className='p-2 text-black rounded border-2 border-slate-700 mt-2'>
                      <span className="text-[24px] text-black font-semibold flex items-center">
                        {this.getIconByPlatform(result.platform as Platform)} {result.title}
                      </span>
                      <span className="text-[15px] text-black font-medium block">
                        (by {result.author}, {this.getFormattedTime(result.time)})
                        </span>
                      {result.content.map((text_part, index) => {
                        return (
                          <span key={index} className={(text_part.bold ? 'font-bold' : '') + " text-lg"}>
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
      </div>
    );  
  }

  startIndex = () => {
    try {
        const response = axios.post("http://localhost:8000/example-index").then(response => {});
    } catch (error) {
      console.error(error);
    }
  }

  onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      this.search();
    }
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
      

  handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState({query: event.target.value});
  }

  clear = () => {
    this.setState({results: [], query: ""});
  }

  search = () => {
    this.setState({isLoading: true});
    try {
        const response = axios.get<SearchResult[]>("http://localhost:8000/search?query=" + this.state.query).then(
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

