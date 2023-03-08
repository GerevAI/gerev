import * as React from "react";

import axios from 'axios';
import ClipLoader from "react-spinners/ClipLoader";
import { BsSearch, BsXLg } from "react-icons/bs";
import { FaConfluence, FaSlack, FaGoogleDrive } from "react-icons/fa";

import EnterImage from './assets/images/enter.svg';


import './assets/css/App.css';


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
    this.state = {query: "Ask any workplace question", results: [], isLoading: false};
  }


  render() {
    return (
      <div className="bg-[#181212] w-screen h-screen flex">
        <div className='absolute'>
          <button onClick={this.startIndex} className='bg-[#886fda] ml-3 text-white p-2 rounded border-2 border-white-700
              hover:bg-[#ddddddd1] hover:text-[#060117] transition duration-500 ease-in-out m-2'>
                Index
          </button>
        </div>
        <div className='flex flex-col items-center mx-auto my-40 w-full'>
          <h1 className='text-7xl text-center text-white m-10'>🧦 gerev.ai</h1>
          <div className="h-[49.5px] w-[38%] rounded-b-[10px] rounded-t-[14px] bg-gradient-to-r from-yellow-400 via-red-500 to-yellow-500">
            <div className='flex h-12 w-full items-center container text-3xl rounded-[10px] bg-[#2A2A2A] text-[#C9C9C9]'>
              
              <button onClick={this.search} className='mx-2 text-white p-2 rounded
               hover:text-[#493294] transition duration-500 ease-in-out flex items-center'>
                {this.state.isLoading ?
                <ClipLoader
                  color="#ffffff"
                  loading={this.state.isLoading}
                  size={25}
                  aria-label="Loading Spinner"
                /> : <BsSearch size={20} className="text-[#D2D2D2] hover:text-[#ebebeb] hover:cursor-pointer"></BsSearch>}
              </button>
              <input type="text" className='w-full font-poppins font-medium leading-7 text-lg p-2 rounded text-[#C9C9C9] bg-transparent !outline-none'
                     placeholder='Search' value={this.state.query} onChange={this.handleChange} onKeyDown={this.onKeyDown} />
              {this.state.results.length > 0 &&
                <BsXLg onClick={this.clear} size={23} className='text-[#8E8C8C] mr-4 hover:text-[#c1bebe] hover:cursor-pointer'></BsXLg>
              }
            </div>

          </div>
            <button className="h-9 w-28 mt-8 p-3 flex items-center justify-center bg-[#2A2A2A] rounded border-[.5px] border-[#6e6e6e88]">
              <span className="font-bold text-[15px] text-[#B3B3B3]">Search</span>
              <img src={EnterImage}></img>
            </button>
       
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
    );  
  }

  startIndex = () => {
    try {
        const response = axios.post("http://localhost:8000/index-confluence").then(response => {});
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

