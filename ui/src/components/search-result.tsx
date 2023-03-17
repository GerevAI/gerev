/* 
This file contains the code for the <SearchResult/> Component.
See "SearchResultProps" on this document for the the properties this component
uses.
*/

import React from 'react';

// If not working, run "npm install react-icons"
import { FaConfluence, FaSlack, FaGoogleDrive } from "react-icons/fa";

// This imports the full-color icons
import BlueFolder from './assets/images/blue-folder.svg';
import Slack from './assets/images/slack.svg';
import Confluence from './assets/images/confluence.svg';
import Drive from './assets/images/google-drive.svg'

export interface TextPart {
  content: string
  bold: boolean
}

export enum ResultType {
  Docment = "document",
  Message = "message",
  Comment = "comment",
  Person = "person"
}

export enum Platform {
  Confluence = "confluence",
  Slack = "slack",
  Drive = "drive"
}

// These are the attributes of a <SearchResult/> element.
export interface SearchResultProps {
  title: string
  author: string
  author_image_url: string
  author_image_data: string
  time: string
  content: TextPart[]
  score: number
  location: string
  platform: string
  type: ResultType
  url: string
}

export const SearchResult = (props: SearchResultProps) => {
  return (
    <div className="mb-4 pt-2">
      <a className="relative text-sm float-right text-white right-2 top-2">{props.score}%</a>
      <div className="flex flex-row items-start">
        <div className="relative w-[60px]">
          {ProfilePic(props.author_image_url, props.platform as Platform, props.type)}
        </div>
        <p className='p-2 pt-0 ml-1 text-[#A3A3A3] text-sm font-poppins'>
          <a className="text-[24px] text-[#A78BF6] text-xl font-poppins font-medium hover:underline hover:cursor-pointer" href={props.url} target='_blank'>
            {props.title}
          </a>
          <span className="flex flex-row text-[15px] font-medium mb-4 mt-1">
            {
              props.type == ResultType.Docment && <img className="inline-block mr-2" src={BlueFolder}></img>
            }
            <span className="ml-0 text-[#D5D5D5]">
              {
                props.type == ResultType.Message && <span>#</span>
              }
              {props.location} ·&thinsp;
            </span>
            <span className="flex flex-row items-center">
              <img className="inline-block ml-2 mr-2 h-4 rounded-xl" src={props.author_image_data ? props.author_image_data : props.author_image_url}></img>
              <span className='capitalize'>{props.author} ·</span>
            </span>
            <span>
              &thinsp;Updated {getFormattedTime(props.time)}&thinsp; |&thinsp;
            </span>
            <span className="flex flex-row items-center">
              {getSmallIconByPlatform(props.platform as Platform)}
              <span className="text-[#A3A3A3]">{props.platform}</span>
            </span>
          </span>

          {props.type == ResultType.Docment &&
            <span>
              {props.content.map((text_part, index) => {
                return (
                  <span key={index} style={{ wordBreak: 'break-word' }} className={(text_part.bold ? 'font-bold text-white' : '') +
                    " text-md font-poppins font-medium"}>
                    {text_part.content}
                  </span>
                )
              })}
            </span>
          }
          {props.type == ResultType.Message &&
            <p className="bg-[#352C45] p-2 px-4 rounded-lg font-poppins leading-[28px] border-b-[#916CCD] border-b-2">
              {props.content.map((text_part, index) => {
                return (
                  <span key={index} className={(text_part.bold ? 'font-bold text-white' : '') +
                    " fony-[14px] font-regular"}>
                    {text_part.content}
                  </span>
                )
              })}
            </p>
          }
        </p>
      </div>
    </div>
  );
}


function getFormattedTime(time: string) {
  let date = new Date(time);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getSmallIconByPlatform(platform: Platform) {
  let classes = "inline mx-1 fill-[#A3A3A3]";
  switch (platform) {
    case Platform.Confluence:
      return <FaConfluence className={classes}></FaConfluence>
    case Platform.Slack:
      return <FaSlack className={classes}></FaSlack>
    case Platform.Drive:
      return <FaGoogleDrive className={classes}></FaGoogleDrive>
  }
}

function getBigColorIconByPlatform(platform: Platform) {
  let classes = "company-logo rounded-full w-1/2 h-1/2 absolute object-cover -right-1.5 -bottom-1.5 bg-white";
  switch (platform) {
    case Platform.Confluence:
      return <img className={classes} src={Confluence} alt={platform}></img>
    case Platform.Slack:
      return <img className={classes} src={Slack} alt={platform}></img>
    case Platform.Drive:
      return <FaGoogleDrive className={classes}></FaGoogleDrive>
  }
}

function ProfilePic(profilePicture, platform, ResultType) {
  /*
  This function displays an image: either a profile picture or a logo.
  The first parameter is the path/url to the profile picture.
  The second parameter is the platform name.
  */
  platform = platform.toLowerCase();
  let profileStyle = "rounded-full w-full h-full object-cover";
  if (platform === "slack") {
    return (
      <div>
        <img className={profileStyle} alt="Profile" src={profilePicture} />
        {getBigColorIconByPlatform(platform)}
      </div>
    );
  }
  else {
    let classes = "w-full h-full object-cover"
    if (platform === "confluence") {
      return (
        <img className={classes} alt="Profile" src={Confluence} />
      );
    }
    if (platform === "drive") {
      return <img className={classes} alt="Profile" src={Drive} />
    }
  }
}

